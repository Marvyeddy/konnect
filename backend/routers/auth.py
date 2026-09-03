from typing import Annotated, Any

from authlib.integrations.base_client import MismatchingStateError
from authlib.integrations.starlette_client import OAuth
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Header,
    Response,
    status,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.constants.main import REFRESH_EXPIRY_TOKEN, SESSION_EXPIRY_TOKEN
from backend.core.config import config as cfg
from backend.core.logging import get_app_logger
from backend.core.security import (
    create_refresh_token,
    create_session_token,
    create_url_safe_token,
    decode_token,
    decode_url_safe_token,
    hash_pwd,
    verify_pwd,
)
from backend.errors import (
    ConfirmPasswordException,
    TokenException,
    UserAlreadyExists,
    UserCredentialInvalid,
)
from backend.external.database import get_session
from backend.external.email import send_email
from backend.external.redis import add_token_to_blocklist
from backend.models.users import Users
from backend.schemas.auth import ResetIn, UserIn, UserLogin
from backend.services.auth import AuthService

auth_router = APIRouter()
auth_service = AuthService()
logger = get_app_logger(__name__)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=cfg.GOOGLE_CLIENT_ID,
    client_secret=cfg.GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    authorize_params={"scope": "openid email profile"},
    access_token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope": "openid email profile"},
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
)


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_new_user(
    bg_tasks: BackgroundTasks,
    user_data: UserIn,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    email = user_data.email

    logger.info(f"Signup attempt for email: {email}")

    user = await auth_service.get_user_by_email(email, session)

    if user is not None:
        logger.warning(f"Signup failed: User with email {email} already exists.")
        raise UserAlreadyExists

    new_user = await auth_service.create_user(user_data, session)

    logger.info(f"User created successfully with email: {email} (id={new_user.id})")

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

    logger.info(f"Session and refresh tokens generated for user id {new_user.id}")

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

    logger.info(f"Signup process completed for email: {email}")

    return response


@auth_router.post("/signin")
async def login_user(
    user_data: UserLogin, session: Annotated[AsyncSession, Depends(get_session)]
):
    email = user_data.email
    password = user_data.password

    logger.info(f"Login attempt for email: {email}")

    user = await auth_service.get_user_by_email(email, session)
    if user is None:
        logger.warning(f"Login failed: Invalid credentials for email: {email}")
        raise UserCredentialInvalid

    if not verify_pwd(password, user.password):
        logger.warning(f"Login failed: Incorrect password for email: {email}")
        raise UserCredentialInvalid

    await auth_service.update_user(user.id, {"auth_provider": "local"}, session)

    token_dict = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    }
    session_token = create_session_token(token_dict)
    refresh_token = create_refresh_token(token_dict)

    logger.info(f"Login successful for email: {email} (user id: {user.id})")

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

    logger.info(f"Tokens set in cookies for email: {email}")

    return response


@auth_router.post("/forget-password")
async def forget_password(
    bg_tasks: BackgroundTasks,
    email: str,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    logger.info(f"Forget password request received for email: {email}")
    user = await auth_service.get_user_by_email(email, session)

    if user:
        logger.info(f"User with email {email} found. Sending password reset email.")
        token = create_url_safe_token({"email": email})
        link = f"http://localhost:3000/reset-password/{token}"

        context = {
            "subject": "Reset your password",
            "link": link,
        }

        bg_tasks.add_task(
            send_email,
            subject=context["subject"],
            recipients=[email],
            template_name="reset_password.html",
            context=context,
        )
    else:
        logger.info(f"Password reset email requested for nonexistent email: {email}")

    return JSONResponse(
        content={
            "message": "If an account with that email exists, a password reset link has been sent."
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/reset-password/{token}")
async def reset_password(
    token: str,
    reset_data: ResetIn,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    logger.info(f"Password reset attempt with token: {token}")

    token_data = decode_url_safe_token(token)
    if not token_data or "email" not in token_data:
        logger.warning("Password reset failed: invalid or tampered token.")
        raise UserCredentialInvalid

    email = token_data["email"]
    user = await auth_service.get_user_by_email(email, session)

    if not user:
        logger.warning(f"Password reset failed: No user found for email: {email}")
        raise UserCredentialInvalid

    new_password = reset_data.new_password
    confirm_password = reset_data.confirm_password

    if confirm_password != new_password:
        logger.warning(
            f"Password reset failed for {email}: password and confirm_password do not match"
        )
        raise ConfirmPasswordException

    await auth_service.update_user(
        user.id, {"password": hash_pwd(new_password)}, session
    )

    logger.info(f"Password reset successfully for user id: {user.id}, email: {email}")

    return JSONResponse(
        content={"message": "Password reset successfully"},
        status_code=status.HTTP_200_OK,
    )


@auth_router.get("/refresh")
async def refresh_session_token(
    authorization: Annotated[str | None, Header()] = None,
    refresh_token: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    session: Annotated[AsyncSession | None, Depends(get_session)] = None,
):
    token = refresh_token

    if not token and authorization:
        scheme, _, bearer_token = authorization.partition(" ")
        if scheme.lower() == "bearer" and bearer_token:
            token = bearer_token

    if not token:
        logger.warning("No refresh token provided")
        raise TokenException

    token_data = decode_token(token)
    if not token_data or "type" not in token_data or token_data["type"] != "refresh":
        logger.warning("Invalid refresh token provided")
        raise TokenException

    token_data = decode_token(token)
    if not token_data or "sub" not in token_data:
        logger.warning("Invalid refresh token provided")
        raise TokenException

    user_id = token_data["sub"]
    user = await auth_service.get_user_by_id(user_id, session)

    if not user:
        logger.warning(f"User not found for refresh token: {user_id}")
        raise TokenException

    new_token_dict = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    }

    new_session_token = create_session_token(new_token_dict)
    new_refresh_token = create_refresh_token(new_token_dict)

    logger.info(f"Session and refresh tokens refreshed for user id: {user.id}")

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Session and refresh tokens refreshed",
            "session_token": new_session_token,
            "refresh_token": new_refresh_token,
        },
    )
    response.set_cookie(
        key="session_token",
        value=new_session_token,
        max_age=SESSION_EXPIRY_TOKEN,
        samesite="Lax",
        httponly=True,
        secure=False,
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        max_age=REFRESH_EXPIRY_TOKEN,
        samesite="Lax",
        httponly=True,
        secure=False,
    )

    logger.info(f"Refresh tokens refreshed for user id: {user.id}")
    return response


@auth_router.get("/logout")
async def logout_user(
    authorization: Annotated[str | None, Header()] = None,
    x_refresh_token: Annotated[str | None, Header(alias="X-Refresh-Token")] = None,
    session_cookie: Annotated[str | None, Cookie(alias="session_token")] = None,
    refresh_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
):
    logger.info("Logout request received")
    tokens_to_revoke: dict[str, Any] = {}

    # ------ Authorization ------------

    if authorization:
        scheme, _, bearer_token = authorization.partition(" ")

        if scheme.lower() == "bearer" and bearer_token:
            token_data = decode_token(bearer_token)

            if token_data:
                token_type = token_data["type"]

                if token_type == "session":
                    tokens_to_revoke[bearer_token] = SESSION_EXPIRY_TOKEN
                elif token_type == "refresh":
                    logger.warning("Refresh token supplied as Authorization token")
                else:
                    logger.warning("Unknown token type supplied during logout")

    # ------ Mobile Refresh Token -----------

    if x_refresh_token:
        token_data = decode_token(x_refresh_token)

        if token_data:
            token_type = token_data.get("type")

            if token_type == "refresh":
                tokens_to_revoke[x_refresh_token] = REFRESH_EXPIRY_TOKEN
            else:
                logger.warning("Invalid refresh token type supplied during logout")

    # ------- SESSION COOKIE -----------

    if session_cookie:
        token_data = decode_token(session_cookie)

        if token_data:
            token_type = token_data["type"]

            if token_type == "session":
                tokens_to_revoke[session_cookie] = SESSION_EXPIRY_TOKEN

    # --------- REFRESH COOKIE ------------

    if refresh_cookie:
        token_data = decode_token(refresh_cookie)

        if token_data:
            token_type = token_data["type"]

            if token_type == "refresh":
                tokens_to_revoke[refresh_cookie] = REFRESH_EXPIRY_TOKEN

    for token, expiry in tokens_to_revoke.items():
        await add_token_to_blocklist(token, expiry)

    response = Response(
        content='{"message": "Logout successfully"}',
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )

    response.delete_cookie(key="session_token")
    response.delete_cookie(key="refresh_token")

    logger.info(
        "Logout successful. revoked_tokens=%s",
        len(tokens_to_revoke),
    )

    return response


# ---------------------------
# GOOGLE AUTHERNTICATION
# ---------------------------
@auth_router.get("/google")
async def auth_google(request: Request):
    logger.info("Google auth initiated.")
    redirect_uri = cfg.GOOGLE_REDIRECT_URI or str(
        request.url_for("auth_google_callback")
    )
    logger.info(f"Redirecting to Google OAuth with redirect_uri: {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get("/google/callback")
async def google_callback(
    bg_tasks: BackgroundTasks,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        logger.info("Google OAuth callback received.")

        token = await oauth.google.authorize_access_token(request)
        logger.info("Google access token retrieved.")

        user_info = token.get("userinfo") or {}

        user_email = user_info.get("email")
        google_id = user_info.get("sub")

        if not user_email or not google_id:
            logger.error(
                "Google login failed: missing user_info (email or sub missing)"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Failed to retrieve user information from Google."},
            )

        user = await auth_service.get_user_by_email(user_email, session)

        if user:
            logger.info(f"Existing user with email {user_email} logging in via Google.")
            google_dict = {"google_id": google_id, "auth_service": "google"}
            await auth_service.update_user(user.id, google_dict, session)
        else:
            logger.info(f"Creating new user via Google with email: {user_email}")
            new_user = Users(
                email=user_email,
                username=user_email.split("@")[0],
                google_id=google_id,
                auth_provider="google",
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            logger.info(
                f"New Google user created, id: {new_user.id}, email: {user_email}"
            )

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

            logger.info(
                f"Session and refresh tokens created for Google user id: {new_user.id}"
            )
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

            logger.info(f"Google signup and session completed for email: {user_email}")
            return response

        # If user existed and was just updated, generate and return tokens as in regular login:
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
                "message": "Logged in successfully (Google)",
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
        logger.info(f"Google login/token set for existing user: {user_email}")
        return response

    except MismatchingStateError as e:
        logger.warning(f"Google OAuth state mismatch or expired session: {e!s}")
        return RedirectResponse(
            url="http://localhost:3000/login?error=session_expired",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception:
        logger.exception("Exception occurred during Google OAuth sign up/login")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error. Please try again later."},
        )
