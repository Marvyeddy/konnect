import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Query, status

from backend.core.security import decode_token
from backend.external.database import get_session
from backend.external.redis import token_in_blocklist
from backend.models.users import Users
from backend.services.auth import AuthService

auth_service = AuthService()


async def get_current_user(
    authorization: Annotated[str | None, Header(...)] = None,
    session_token: Annotated[str | None, Cookie(alias="session_token")] = None,
    token_query: Annotated[str | None, Query(alias="token")] = None,
    session: Annotated[str | None, Depends(get_session)] = None,
):
    token = session_token

    # Try header if no cookie session
    if not token and authorization:
        scheme, _, bearer_token = authorization.partition(" ")
        if scheme.lower() == "bearer" and bearer_token:
            token = bearer_token

    # Try query param if still no token
    if not token and token_query:
        token = token_query

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token missing.",
        )

    if await token_in_blocklist(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired or is invalid.",
        )

    if token_data.get("type") != "session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user id.",
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user id in token.",
        )

    user = await auth_service.get_user_by_id(user_uuid, session)

    if not user or getattr(user, "is_active", None) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


async def get_user_role(
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not current_user or not getattr(current_user, "role", None):
        raise credentials_exception
    return current_user.role


async def get_user_permission(
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    permission = (
        getattr(getattr(current_user, "user_profile", None), "permission_level", None)
        if current_user
        else None
    )
    if not current_user or not permission:
        raise credentials_exception
    return permission
