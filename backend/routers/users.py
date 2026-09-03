import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.constants.main import REFRESH_EXPIRY_TOKEN, SESSION_EXPIRY_TOKEN
from backend.core.logging import get_app_logger
from backend.core.security import decode_token
from backend.dependencies import get_current_user
from backend.external.database import get_session
from backend.external.redis import add_token_to_blocklist
from backend.models.users import Users
from backend.services.auth import AuthService

user_router = APIRouter()
auth_service = AuthService()
logger = get_app_logger(__name__)


@user_router.get("/me")
async def get_user_profile(
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource.",
        )
    return current_user


@user_router.delete("/delete")
async def delete_user_account(
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
