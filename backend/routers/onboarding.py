import uuid
from typing import Annotated

import cloudinary.uploader
from cloudinary.exceptions import BadRequest, Error
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_user
from backend.external.database import get_session
from backend.models.notification import Notification
from backend.models.user_profile import UserProfile
from backend.models.users import Users
from backend.models.vendor_profile import VendorProfile
from backend.schemas.onboarding import VendorOnboarding
from backend.services.auth import AuthService
from backend.services.sse_manager import notification_manager
from backend.core.logging import get_app_logger

onboarding_router = APIRouter()
auth_service = AuthService()

logger = get_app_logger(__name__)


@onboarding_router.post("/user")
async def onboard_user(
    full_name: Annotated[str, Form()],
    image: Annotated[UploadFile | None, File()] = None,
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
):
    image_url = None

    if image:
        allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
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

        allowed_content_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if image.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file content type",
            )

        try:
            unique_id = uuid.uuid4().hex[:8]
            base_filename = (
                image.filename.rsplit(".", 1)[0]
                if "." in image.filename
                else image.filename
            )

            upload_result = await run_in_threadpool(
                cloudinary.uploader.upload,
                file_bytes,
                public_id=f"users/profiles/{base_filename}_{unique_id}",
                overwrite=True,
            )
            image_url = upload_result.get("secure_url")

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

    return {
        "message": "User onboarded successfully",
        "user_profile": user_profile,
    }


@onboarding_router.post("/vendor")
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

    # -------------------------------------------------------------
    # PHASE 1: BULK VALIDATION (Fail fast before uploading anything)
    # -------------------------------------------------------------
    allowed_img_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
    allowed_img_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}

    if image:
        img_ext = image.filename.split(".")[-1].lower() if "." in image.filename else ""
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

        await image.seek(0)

    # Validate Business License File
    allowed_lic_extensions = {"jpg", "jpeg", "png", "pdf"}
    allowed_lic_types = {"image/jpeg", "image/png", "application/pdf"}

    lic_ext = (
        business_license.filename.split(".")[-1].lower()
        if "." in business_license.filename
        else ""
    )
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
    await business_license.seek(0)

    # -------------------------------------------------------------
    # PHASE 2: CLOUDINARY UPLOADS
    # -------------------------------------------------------------
    image_url = None
    if image:
        file_bytes = await image.read()
        try:
            unique_id = uuid.uuid4().hex[:8]
            # FIX: Added [0] index to resolve the raw array split text bug
            base_img_name = (
                image.filename.rsplit(".", 1)[0]
                if "." in image.filename
                else image.filename
            )

            upload_result = await run_in_threadpool(
                cloudinary.uploader.upload,
                file_bytes,
                public_id=f"vendors/profiles/{base_img_name}_{unique_id}",
                overwrite=True,
            )
            image_url = upload_result.get("secure_url")
        except (BadRequest, Error) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Profile image upload failed: {e!s}",
            )

    # Upload Business License
    lic_bytes = await business_license.read()
    try:
        unique_id = uuid.uuid4().hex[:8]
        base_lic_name = (
            business_license.filename.rsplit(".", 1)[0]
            if "." in business_license.filename
            else business_license.filename
        )

        license_upload_result = await run_in_threadpool(
            cloudinary.uploader.upload,
            lic_bytes,
            public_id=f"vendors/licenses/{base_lic_name}_{unique_id}",
            overwrite=True,
            resource_type="auto",
        )
        license_url = license_upload_result.get("secure_url")
    except (BadRequest, Error) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Business license upload failed: {e!s}",
        )

    # -------------------------------------------------------------
    # PHASE 3: DATABASE PERSISTENCE & NOTIFICATIONS
    # -------------------------------------------------------------
    new_vendor = VendorProfile(
        **vendor_data.model_dump(),
        user_id=current_user.id,
        image=image_url,
        business_license=license_url,
    )

    await auth_service.update_user(current_user.id, {"role": "pending"}, session)
    session.add(new_vendor)
    await session.commit()
    await session.refresh(new_vendor)

    try:
        admin_query = await session.execute(
            select(Users.id).where(Users.role == "admin")
        )
        admin_ids = [str(row[0]) for row in admin_query.all()]

        if admin_ids:
            notifications_to_add = [
                Notification(
                    user_id=admin_id,
                    title="New vendor verification required",
                    message=f"Vendor '{vendor_data.business_name}' has onboarded and requires document review.",
                    notification_type="VENDOR_ONBOARDING",
                    action_url=f"/admin/vendors/{new_vendor.id}",
                    is_read=False,
                )
                for admin_id in admin_ids
            ]
            session.add_all(notifications_to_add)
            await session.commit()

            live_payload = {
                "title": "New Vendor Verification Required",
                "message": f"Vendor '{vendor_data.business_name}' has onboarded and requires document review.",
                "notification_type": "VENDOR_ONBOARDING",
                "action_url": f"/admin/vendors/{new_vendor.id}",
                "vendor_id": str(new_vendor.id),
            }
            await notification_manager.broadcast_to_admins(admin_ids, live_payload)
    except Exception as log_err:
        logger.error(f"Notification broadcasting failed: {log_err}")

    return {
        "message": "Vendor onboarded successfully",
        "vendor_id": str(new_vendor.id),
        "license_url": license_url,
        "image_url": image_url,
    }
