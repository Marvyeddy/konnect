from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.constants.main import REFRESH_EXPIRY_TOKEN, SESSION_EXPIRY_TOKEN
from backend.core.security import create_refresh_token, create_session_token, verify_pwd
from backend.errors import UserAlreadyExists, UserCredentialInvalid
from backend.external.database import get_session
from backend.external.email import send_email
from backend.schemas.auth import UserIn, UserLogin
from backend.services.auth import AuthService

auth_router = APIRouter()
auth_service = AuthService()


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_new_user(
    bg_tasks: BackgroundTasks,
    user_data: UserIn,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    email = user_data.email

    user = await auth_service.get_user_by_email(email, session)

    if user is not None:
        raise UserAlreadyExists

    new_user = await auth_service.create_user(user_data, session)

    context = {
        "subject": "Welcome to Konnect!",
        "body_text": (f"Hi {new_user.username}"),
    }

    bg_tasks.add_task(
        send_email,
        subject="Welcome to Konnect!",
        recipients=[new_user.email],
        template_name="welcome.html",
        context=context,
    )

    token_dict = {
        "sub": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role,
    }

    session_token = create_session_token(token_dict)
    refresh_token = create_refresh_token(token_dict)

    response = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "User created successfully",
            "session_token": session_token,
            "refresh_token": refresh_token,
        },
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=SESSION_EXPIRY_TOKEN,
        samesite="Lax",
        httponly=True,
        secure=False,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_EXPIRY_TOKEN,
        samesite="Lax",
        httponly=True,
        secure=False,
    )

    return response


@auth_router.post("/signin")
async def login_user(
    user_data: UserLogin, session: Annotated[AsyncSession, Depends(get_session)]
):
    email = user_data.email
    password = user_data.password

    user = await auth_service.get_user_by_email(email, session)

    if user is None:
        raise UserCredentialInvalid

    password_valid = verify_pwd(password, user.password)

    if not password_valid:
        raise UserCredentialInvalid

    token_dict = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    }

    session_token = create_session_token(token_dict)
    refresh_token = create_refresh_token(token_dict)

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Logged in successfully",
            "session_token": session_token,
            "refresh_token": refresh_token,
        },
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=SESSION_EXPIRY_TOKEN,
        samesite="Lax",
        httponly=True,
        secure=False,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_EXPIRY_TOKEN,
        samesite="Lax",
        httponly=True,
        secure=False,
    )

    return response
