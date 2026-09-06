import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.authorization import PermissionChecker
from backend.external.database import get_session
from backend.services.auth import AuthService

admin_router = APIRouter()
auth_service = AuthService()

super_admin = PermissionChecker(["super_admin"])


@admin_router.patch("/{user_id}/create", dependencies=[Depends(super_admin)])
async def make_admin(
    user_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    update_fields = {"role": "admin"}
    updated_user = await auth_service.update_user(user_uuid, update_fields, session)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role.",
        )

    profile = getattr(updated_user, "user_profile", None)
    if profile and hasattr(profile, "permission_level"):
        profile.permission_level = "manager"

    try:
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during promotion.",
        )

    return {"message": f"User {user_id} is now an admin."}


@admin_router.patch("/{user_id}/remove", dependencies=[Depends(super_admin)])
async def remove_admin(
    user_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    update_fields = {"role": "user"}
    updated_user = await auth_service.update_user(user_uuid, update_fields, session)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role.",
        )

    profile = getattr(updated_user, "user_profile", None)
    if profile and hasattr(profile, "permission_level"):
        profile.permission_level = None

    try:
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while removing admin privileges.",
        )

    return {"message": f"User {user_id} has been stripped of admin privileges."}
