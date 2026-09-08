import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.authorization import PermissionChecker, RoleChecker
from backend.external.database import get_session
from backend.services.auth import AuthService

admin_router = APIRouter()
auth_service = AuthService()

super_admin = PermissionChecker(["super_admin"])
admin = RoleChecker(["admin"])


@admin_router.get("/create/{user_id}", dependencies=[Depends(super_admin)])
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


@admin_router.get("/remove/{user_id}", dependencies=[Depends(super_admin)])
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


# verify a vendor
@admin_router.get("/verify/{user_id}", dependencies=[Depends(admin)])
async def verify_vendor(
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

    if user.role != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not pending verification.",
        )

    user.role = "vendor"
    profile = getattr(user, "vendor_profile", None)
    if profile is not None and hasattr(profile, "is_verified"):
        profile.is_verified = True

    try:
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify vendor.",
        )

    return {"message": f"User {user_id} has been verified as a vendor."}


@admin_router.get("/inactive/{user_id}", dependencies=[Depends(admin)])
async def user_inactive(
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

    user.is_active = False

    try:
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set user as inactive.",
        )

    return {"message": f"User {user_id} has been set to inactive."}


@admin_router.get("/active/{user_id}", dependencies=[Depends(admin)])
async def user_active(
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

    user.is_active = True

    try:
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set user as active.",
        )

    return {"message": f"User {user_id} has been set to active."}
