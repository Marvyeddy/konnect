import uuid
from typing import Annotated

import cloudinary.uploader
from cloudinary.exceptions import BadRequest, Error
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import hash_pwd
from backend.dependencies import get_current_user
from backend.external.database import get_session
from backend.models.users import Users
from backend.schemas.vendors import UserOut, VendorUpdate

vendor_router = APIRouter()


@vendor_router.get("/me", response_model=UserOut)
async def get_vendor_profile(
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource.",
        )
    return current_user


@vendor_router.patch("/me/update")
async def update_vendor_profile(
    vendor_data_str: Annotated[str, Form(alias="vendor_data")],
    image: Annotated[UploadFile | None, File()] = None,
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
):
    try:
        vendor_data = VendorUpdate.model_validate_json(vendor_data_str)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    updated = False
    image_url = current_user.vendor_profile.image

    if image:
        allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
        file_extension = (
            image.filename.split(".")[-1].lower() if "." in image.filename else ""
        )

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file extension"
            )

        allowed_content_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if image.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file content type",
            )

        file_bytes = await image.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size is too large (Max 10MB)",
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
                public_id=f"vendors/profiles/{base_filename}_{unique_id}",
                overwrite=True,
            )
            image_url = upload_result.get("secure_url")
            current_user.vendor_profile.image = image_url
            updated = True
        except (BadRequest, Error) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cloudinary upload failed: {e!s}",
            )
    if vendor_data.username is not None:
        current_user.username = vendor_data.username
        updated = True
    if vendor_data.password is not None:
        current_user.password = hash_pwd(vendor_data.password)
        updated = True
    if vendor_data.full_name is not None:
        current_user.vendor_profile.full_name = vendor_data.full_name
        updated = True
    if vendor_data.address is not None:
        current_user.vendor_profile.address = vendor_data.address
        updated = True
    if vendor_data.phone_number is not None:
        current_user.vendor_profile.phone_number = vendor_data.phone_number
        updated = True

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    if session is not None:
        session.add(current_user)
        await session.commit()
        await session.refresh(current_user)

    return {
        "message": "Profile updated successfully",
    }
