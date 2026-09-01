import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status

from backend.constants.main import Roles
from backend.core.security import decode_token
from backend.external.database import get_session
from backend.external.redis import token_in_blocklist
from backend.models.users import Users
from backend.services.auth import AuthService

auth_service = AuthService()


async def get_current_user(
    authorization: Annotated[str | None, Header(...)] = None,
    session_token: Annotated[str | None, Cookie(alias="session_token")] = None,
    session: Annotated[str | None, Depends(get_session)] = None,
):
    token = session_token

    if not token and authorization:
        schemes, _, bearer_token = authorization.partition(" ")

        if schemes.lower() == "bearer" and bearer_token:
            token = bearer_token

    if token is None:
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

    if token_data.get("type") != "session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired or is invalid.",
        )

    user_id = uuid.UUID(token_data["sub"])

    user = await auth_service.get_user_by_id(user_id, session)

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


class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(
        self, user_role: Annotated[Roles | None, Depends(get_user_role)] = None
    ):
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return user_role
