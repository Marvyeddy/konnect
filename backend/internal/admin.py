import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.authorization import PermissionChecker, RoleChecker
from backend.constants.main import ReportStatus
from backend.external.database import get_session
from backend.external.email import send_email
from backend.schemas.vendor_meta import ReportRead, ReportReview
from backend.services.auth import AuthService
from backend.core.logging import get_app_logger
from backend.services.reports import ReportService

admin_router = APIRouter()
auth_service = AuthService()
report_service = ReportService()
logger = get_app_logger(__name__)

super_admin = PermissionChecker(["super_admin"])
admin = RoleChecker(["admin"])


@admin_router.get("/create/{user_id}", dependencies=[Depends(super_admin)])
async def make_admin(
    user_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    logger.info(f"Attempting to promote user {user_id} to admin.")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for make_admin: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)
    if not user:
        logger.warning(f"User {user_id} not found for admin promotion.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    update_fields = {"role": "admin"}
    updated_user = await auth_service.update_user(user_uuid, update_fields, session)
    if not updated_user:
        logger.error(f"Failed to update user {user_id} role to admin.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role.",
        )

    profile = getattr(updated_user, "user_profile", None)
    if profile and hasattr(profile, "permission_level"):
        profile.permission_level = "manager"

    try:
        await session.commit()
        logger.info(f"User {user_id} promoted to admin successfully.")
    except Exception as e:  # noqa: BLE001
        await session.rollback()
        logger.error(f"Database error during promotion of {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during promotion.",
        )

    return {"message": f"User {user_id} is now an admin."}


@admin_router.get("/remove/{user_id}", dependencies=[Depends(super_admin)])
async def remove_admin(
    user_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    logger.info(f"Attempting to remove admin privileges from user {user_id}.")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for remove_admin: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)
    if not user:
        logger.warning(f"User {user_id} not found for admin removal.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    update_fields = {"role": "user"}
    updated_user = await auth_service.update_user(user_uuid, update_fields, session)
    if not updated_user:
        logger.error(f"Failed to update user {user_id} role to user.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role.",
        )

    profile = getattr(updated_user, "user_profile", None)
    if profile and hasattr(profile, "permission_level"):
        profile.permission_level = None

    try:
        await session.commit()
        logger.info(f"User {user_id} admin privileges removed successfully.")
    except Exception as e:  # noqa: BLE001
        await session.rollback()
        logger.error(
            f"Database error while removing admin privileges from {user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while removing admin privileges.",
        )

    return {"message": f"User {user_id} has been stripped of admin privileges."}


# verify a vendor
@admin_router.get("/verify/{user_id}", dependencies=[Depends(admin)])
async def verify_vendor(
    bg_tasks: BackgroundTasks,
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    logger.info(f"Attempting to verify vendor user {user_id}.")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for verify_vendor: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)
    if not user:
        logger.warning(f"User {user_id} not found for vendor verification.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    if user.role != "pending":
        logger.warning(
            f"User {user_id} is not pending verification. Current role: {user.role}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not pending verification.",
        )

    user.role = "vendor"
    profile = getattr(user, "vendor_profile", None)
    if profile is not None and hasattr(profile, "verified"):
        profile.verified = True

    try:
        await session.commit()
        logger.info(f"User {user_id} has been verified as a vendor.")
    except Exception as e:  # noqa: BLE001
        await session.rollback()
        logger.error(f"Failed to verify vendor {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify vendor.",
        )

    context = {
        "username": user.username,
        "login_url": "http://localhost:3000/login",
    }

    bg_tasks.add_task(
        send_email,
        subject="Your Vendor Account is Verified!",
        recipients=[user.email],
        template_name="vendor_verified.html",
        context=context,
    )

    return {"message": f"User {user_id} has been verified as a vendor."}


@admin_router.get("/unverify/{user_id}", dependencies=[Depends(admin)])
async def unverify_vendor(
    bg_tasks: BackgroundTasks,
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    logger.info(f"Attempting to unverify vendor user {user_id}.")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for unverify_vendor: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)
    if not user:
        logger.warning(f"User {user_id} not found for vendor unverification.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    if user.role != "pending":
        logger.warning(
            f"User {user_id} is not pending verification. Current role: {user.role}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not pending verification.",
        )

    user.role = "pending"

    try:
        await session.commit()
        logger.info(f"User {user_id} has been unverified as a vendor.")
    except Exception as e:  # noqa: BLE001
        await session.rollback()
        logger.error(f"Failed to verify vendor {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify vendor.",
        )

    context = {
        "username": user.username,
        "onboarding_url": f"http://localhost:3000/onboarding/{user_id}",
    }

    bg_tasks.add_task(
        send_email,
        subject="Action Required: Vendor Account Unverified",
        recipients=[user.email],
        template_name="vendor_unverified.html",
        context=context,
    )

    return {"message": f"User {user_id} has been unverified as a vendor."}


# make user or vendor active or inactive
@admin_router.get("/inactive/{user_id}", dependencies=[Depends(admin)])
async def user_inactive(
    user_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    logger.info(f"Attempting to inactivate user {user_id}.")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for user_inactive: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)

    if not user:
        logger.warning(f"User {user_id} not found for inactivation.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    user.is_active = False

    try:
        await session.commit()
        logger.info(f"User {user_id} has been set to inactive.")
    except Exception as e:  # noqa: BLE001
        await session.rollback()
        logger.error(f"Failed to set user {user_id} as inactive: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set user as inactive.",
        )

    return {"message": f"User {user_id} has been set to inactive."}


@admin_router.get("/vendor/{user_id}", dependencies=[Depends(admin)])
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


@admin_router.get("/active/{user_id}", dependencies=[Depends(admin)])
async def user_active(
    user_id: str, session: Annotated[AsyncSession, Depends(get_session)]
):
    logger.info(f"Attempting to activate user {user_id}.")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID format for user_active: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format. Must be a valid UUID.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)

    if not user:
        logger.warning(f"User {user_id} not found for activation.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    user.is_active = True

    try:
        await session.commit()
        logger.info(f"User {user_id} has been set to active.")
    except Exception as e:  # noqa: BLE001
        await session.rollback()
        logger.error(f"Failed to set user {user_id} as active: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set user as active.",
        )

    return {"message": f"User {user_id} has been set to active."}


# Get all users by role using query parameter ?role=vendor
@admin_router.get("/client", dependencies=[Depends(admin)])
async def get_all_users_by_role(
    role: Annotated[
        str, Query(..., description='Role to filter users by, e.g. "vendor"')
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    logger.info(f"Fetching users with role: {role}")
    users = await auth_service.get_user_by_role(role, session)
    if not users:
        logger.warning(f"No users found with role: {role}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No users found with role: {role}",
        )
    logger.info(f"Found {len(users)} users with role: {role}")
    return users


@admin_router.get("", response_model=list[ReportRead], dependencies=[Depends(admin)])
async def list_reports(
    session: Annotated[AsyncSession, Depends(get_session)],
    report_status: Annotated[ReportStatus | None, Query()] = None,
    vendor_id: Annotated[uuid.UUID | None, Query()] = None,
):
    return await report_service.list_reports(
        session=session, report_status=report_status, vendor_id=vendor_id
    )


@admin_router.patch(
    "/{report_id}/review", response_model=ReportRead, dependencies=[Depends(admin)]
)
async def review_report(
    report_id: uuid.UUID,
    review: ReportReview,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await report_service.review_report(
        report_id=report_id,
        new_status=review.status,
        session=session,
    )
