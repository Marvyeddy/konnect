import uuid
from typing import Annotated, Any

import cloudinary.uploader
from cloudinary.exceptions import BadRequest, Error
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Form,
    HTTPException,
    Header,
    Response,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.constants.main import REFRESH_EXPIRY_TOKEN, SESSION_EXPIRY_TOKEN
from backend.core.security import decode_token, hash_pwd
from backend.dependencies import get_current_user
from backend.external.database import get_session
from backend.external.redis import add_token_to_blocklist
from backend.models.users import Users
from backend.schemas.users import UserOut, UserUpdate
from backend.services.auth import AuthService
from backend.core.logging import get_app_logger
from backend.core.rate_limit import guard_decorator

user_router = APIRouter()
auth_service = AuthService()
logger = get_app_logger(__name__)


@user_router.get("/me", response_model=UserOut)
async def get_user_profile(
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource.",
        )
    return current_user


@user_router.patch("/update")
@guard_decorator.rate_limit(requests=20, window=3600)
async def update_profile(
    user_data_str: Annotated[str, Form(alias="user_data")],
    current_user: Annotated[Users, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    image: Annotated[UploadFile | None, File()] = None,
):
    try:
        user_data = UserUpdate.model_validate_json(user_data_str)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    update_dict = user_data.model_dump(exclude_unset=True)

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
                public_id=f"users/profiles/{base_filename}_{unique_id}",
                overwrite=True,
            )
            image_url = upload_result.get("secure_url")
        except (BadRequest, Error) as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {e!s}")

    if not update_dict and not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided.",
        )

    for key, value in update_dict.items():
        if key == "password":
            current_user.password = hash_pwd(value)
        elif key == "full_name":
            current_user.user_profile.full_name = value
        else:
            setattr(current_user, key, value)

    if image_url:
        current_user.user_profile.image = image_url

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return {"message": "Profile updated successfully"}


@user_router.get("/{user_id}")
async def view_userprofile(
    user_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    logger.info(f"Fetching user profile for user {user_id}.")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for view_userprofile: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)
    if not user:
        logger.warning(f"User {user_id} not found for user profile view.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    profile = getattr(user, "user_profile", None)
    if not profile:
        logger.warning(f"No user profile found for user {user_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user profile found for user {user_id}.",
        )

    return profile


@user_router.delete("/delete")
async def delete_account(
    authorization: Annotated[str | None, Header()] = None,
    x_refresh_token: Annotated[str | None, Header(alias="X-Refresh-Token")] = None,
    session_cookie: Annotated[str | None, Cookie(alias="session_token")] = None,
    refresh_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession | None, Depends(get_session)] = None,
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource.",
        )

    user_id = uuid.UUID(str(current_user.id))

    # 2. Delete the user from the database first
    deleted = await auth_service.delete_user(user_id, session)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or already deleted.",
        )

    # 3. Blocklist processing (Mirrors your /logout logic)
    logger.info("Processing token blocklist for deleted user: %s", user_id)
    tokens_to_revoke: dict[str, Any] = {}

    # ------ Authorization Header ------------
    if authorization:
        scheme, _, bearer_token = authorization.partition(" ")
        if scheme.lower() == "bearer" and bearer_token:
            token_data = decode_token(bearer_token)
            if token_data and token_data.get("type") == "session":
                tokens_to_revoke[bearer_token] = SESSION_EXPIRY_TOKEN

    # ------ Mobile Refresh Token Header -----------
    if x_refresh_token:
        token_data = decode_token(x_refresh_token)
        if token_data and token_data.get("type") == "refresh":
            tokens_to_revoke[x_refresh_token] = REFRESH_EXPIRY_TOKEN

    # ------- SESSION COOKIE -----------
    if session_cookie:
        token_data = decode_token(session_cookie)
        if token_data and token_data.get("type") == "session":
            tokens_to_revoke[session_cookie] = SESSION_EXPIRY_TOKEN

    # --------- REFRESH COOKIE ------------
    if refresh_cookie:
        token_data = decode_token(refresh_cookie)
        if token_data and token_data.get("type") == "refresh":
            tokens_to_revoke[refresh_cookie] = REFRESH_EXPIRY_TOKEN

    # Push all identified tokens into the blocklist store
    for token, expiry in tokens_to_revoke.items():
        await add_token_to_blocklist(token, expiry)

    # 4. Construct response and clear out client-side cookies
    response = Response(
        content='{"message": "User account deleted and sessions revoked successfully."}',
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )

    response.delete_cookie(key="session_token")
    response.delete_cookie(key="refresh_token")

    logger.info(
        "User deletion completed. user_id=%s, revoked_tokens=%s",
        user_id,
        len(tokens_to_revoke),
    )

    return response
