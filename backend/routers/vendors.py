import uuid
from typing import Annotated

import cloudinary.uploader
from cloudinary.exceptions import BadRequest, Error
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.authorization import RoleChecker
from backend.core.security import hash_pwd
from backend.dependencies import get_current_user
from backend.external.database import get_session
from backend.models.users import Users
from backend.schemas.vendor_meta import ReportCreate, ReviewCreate, ReviewRead
from backend.schemas.vendors import VendorUpdate
from backend.services.auth import AuthService
from backend.services.reports import ReportService
from backend.services.reviews import VendorReviewService
from backend.core.logging import get_app_logger
from backend.core.rate_limit import guard_decorator


vendor_router = APIRouter()
report_service = ReportService()
review_service = VendorReviewService()
auth_service = AuthService()

logger = get_app_logger(__name__)


@vendor_router.patch("/update")
@guard_decorator.rate_limit(requests=20, window=3600)
async def update_vendor_profile(
    vendor_data_str: Annotated[str, Form(alias="vendor_data")],
    current_user: Annotated[Users, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    image: Annotated[UploadFile | None, File()] = None,
):
    try:
        vendor_data = VendorUpdate.model_validate_json(vendor_data_str)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    update_dict = vendor_data.model_dump(exclude_unset=True)

    image_url = None
    if image:
        allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
        allowed_content_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        file_extension = (
            image.filename.split(".")[-1].lower() if "." in image.filename else ""
        )

        if (
            file_extension not in allowed_extensions
            or image.content_type not in allowed_content_types
        ):
            raise HTTPException(status_code=400, detail="Invalid file type")

        file_bytes = await image.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB")

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
                public_id=f"vendors/profiles/{base_filename}_{unique_id}",
                overwrite=True,
            )
            image_url = upload_result.get("secure_url")
        except (BadRequest, Error) as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {e!s}")

    # No fields to update at all?
    if not update_dict and not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    for key, value in update_dict.items():
        if key == "password":
            current_user.password = hash_pwd(value)
        elif key == "full_name":
            current_user.vendor_profile.full_name = value
        elif key == "address":
            current_user.vendor_profile.address = value
        elif key == "phone_number":
            current_user.vendor_profile.phone_number = value
        else:
            setattr(current_user, key, value)

    if image_url:
        current_user.vendor_profile.image = image_url

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return {"message": "Profile updated successfully"}


@vendor_router.get("/{user_id}")
async def view_vendorprofile(
    user_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    logger.info(f"Fetching vendor profile for user {user_id}.")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for view_vendorprofile: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)
    if not user:
        logger.warning(f"User {user_id} not found for vendor profile view.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    profile = getattr(user, "vendor_profile", None)
    if not profile:
        logger.warning(f"No vendor profile found for user {user_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No vendor profile found for user {user_id}.",
        )

    return profile
