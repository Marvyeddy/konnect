import asyncio
from typing import Annotated

from cloudinary.exceptions import BadRequest, Error
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.constants.cloudinary import upload_to_cloudinary
from backend.dependencies import get_current_user
from backend.external.database import get_session

from backend.models.user_profile import UserProfile
from backend.models.users import Users
from backend.models.vendor_profile import VendorProfile
from backend.schemas.onboarding import VendorOnboarding
from backend.services.auth import AuthService

from backend.core.logging import get_app_logger
from backend.core.rate_limit import guard_decorator
from backend.tasks.notification_tasks import notify_admins_vendor_onboarding

onboarding_router = APIRouter()
auth_service = AuthService()

logger = get_app_logger(__name__)


@onboarding_router.post("/user")
@guard_decorator.rate_limit(requests=5, window=3600)
async def onboard_user(
    full_name: Annotated[str, Form()],
    image: Annotated[UploadFile | None, File()] = None,
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
):
    image_url = None

    if image:
        allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
        allowed_content_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}

        file_extension = (
            image.filename.split(".")[-1].lower() if "." in image.filename else ""
        )

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file extension"
            )

        file_bytes = await image.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size is too large (Max 10MB)",
            )

        if image.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file content type",
            )

        try:
            image_url = await upload_to_cloudinary(
                file_bytes=file_bytes,
                folder="users/profiles",
                filename=image.filename,
                resource_type="image",
            )
        except (BadRequest, Error) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cloudinary upload failed: {e!s}",
            )

    user_profile = UserProfile(
        user_id=current_user.id,
        full_name=full_name,
        image=image_url,
    )

    session.add(user_profile)
    await session.commit()
    await session.refresh(user_profile)

    return {"message": "User onboarded successfully"}


@onboarding_router.post("/vendor")
@guard_decorator.rate_limit(requests=3, window=3600)
async def onboard_vendor(
    vendor_data_str: Annotated[str, Form(alias="vendor_data")],
    business_license: Annotated[UploadFile, File()],
    image: Annotated[UploadFile | None, File()] = None,
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        vendor_data = VendorOnboarding.model_validate_json(vendor_data_str)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    existing_vendor_query = await session.execute(
        select(VendorProfile).where(VendorProfile.user_id == current_user.id)
    )
    existing_vendor = existing_vendor_query.scalar_one_or_none()

    allowed_img_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
    allowed_img_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}

    allowed_lic_extensions = {"jpg", "jpeg", "png", "pdf"}
    allowed_lic_types = {"image/jpeg", "image/png", "application/pdf"}

    image_bytes: bytes | None = None
    if image:
        image_filename = image.filename or ""

        img_ext = image_filename.split(".")[-1].lower() if "." in image_filename else ""
        if img_ext not in allowed_img_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file extension",
            )

        image_bytes = await image.read()
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image size is too large (Max 10MB)",
            )

        if image.content_type not in allowed_img_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image content type",
            )

    license_filename = business_license.filename or ""

    lic_ext = license_filename.split(".")[-1].lower() if "." in license_filename else ""
    if lic_ext not in allowed_lic_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business license extension. Only JPG, PNG, and PDF are allowed.",
        )

    license_bytes = await business_license.read()
    if len(license_bytes) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business license size is too large (Max 15MB)",
        )

    if business_license.content_type not in allowed_lic_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid business license file content type",
        )

    image_url = existing_vendor.image if existing_vendor else None

    try:
        if image_bytes is not None:
            image_url, license_url = await asyncio.gather(
                upload_to_cloudinary(image_bytes, "vendors/profiles", image_filename),
                upload_to_cloudinary(
                    license_bytes,
                    "vendors/licenses",
                    license_filename,
                    resource_type="auto",
                ),
            )
        else:
            license_url = await upload_to_cloudinary(
                license_bytes,
                "vendors/licenses",
                license_filename,
                resource_type="auto",
            )
    except (BadRequest, Error) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload to Cloudinary failed: {e!s}",
        )

    vendor_fields = vendor_data.model_dump()
    vendor_fields.update(
        {
            "image": image_url,
            "business_license": license_url,
            "verified": False,
        }
    )

    if existing_vendor:
        for key, value in vendor_fields.items():
            setattr(existing_vendor, key, value)
        vendor_record = existing_vendor
    else:
        vendor_record = VendorProfile(**vendor_fields, user_id=current_user.id)
        session.add(vendor_record)

    await auth_service.update_user(current_user.id, {"role": "pending"}, session)
    await session.commit()
    await session.refresh(vendor_record)

    notify_admins_vendor_onboarding.delay(
        vendor_id=vendor_record.id,
        business_name=vendor_record.business_name,
        session=session,
        is_update=existing_vendor is None,
    )

    return {
        "message": "Vendor onboarding submitted successfully",
        "vendor_id": str(vendor_record.id),
    }
