from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.constants.main import Roles
from backend.dependencies import get_user_permission, get_user_role


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


class PermissionChecker:
    def __init__(self, allowed_permissions: list[str]):
        self.allowed_permissions = allowed_permissions

    def __call__(
        self,
        user_permission: Annotated[str | None, Depends(get_user_permission)] = None,
    ):
        if user_permission not in self.allowed_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return user_permission
