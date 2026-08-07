from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.database import get_session
from backend.email.email import send_email
from backend.schemas.auth import AuthIn, AuthLogin, AuthOut
from backend.services.auth import AuthServices
from backend.utils.errors import UserExistsException
from backend.utils.logging import get_app_logger
from backend.utils.security import verify_pwd

auth_router = APIRouter()
auth_service = AuthServices()
logger = get_app_logger(__name__)


@auth_router.post(
    "/signup", response_model=AuthOut, status_code=status.HTTP_201_CREATED
)
async def create_user(
    bg_task: BackgroundTasks,
    user_data: AuthIn,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    email_exists = await auth_service.get_user_by_email(user_data.email, session)

    if email_exists:
        logger.warning(f"Attempt to register with existing email: {user_data.email}")
        raise UserExistsException

    new_user = await auth_service.create_user(user_data, session)

    context = {
        "subject": "Welcome to Konnect! Ready to discover and shop? 🛍️",
    }

    await bg_task.add_task(
        send_email,
        subject=context["subject"],
        recipients=[user_data.email],
        template_name="welcome.html",
        template_context=context,
    )

    logger.info(f"New user created: {new_user.email}")
    return new_user


@auth_router.post("/login")
async def login_user(
    user_data: AuthLogin, session: Annotated[AsyncSession, Depends(get_session)]
):
    email = user_data.email
    password = user_data.password

    user = await auth_service.get_user_by_email(email, session)
    if not user:
        logger.warning(f"Failed login attempt: user with email {email} not found.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    valid_password = verify_pwd(password, user.password)
    if not valid_password:
        logger.warning(f"Failed login attempt: invalid password for email {email}.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    logger.info(f"User logged in: {user.email}")
    return user
