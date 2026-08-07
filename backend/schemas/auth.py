import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr


class Roles(Enum):
    USER = "user"
    ADMIN = "admin"
    VENDOR = "vendor"


class AuthLogin(BaseModel):
    email: EmailStr
    password: str


class AuthIn(AuthLogin):
    role: Roles


class AuthOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: Roles
    is_active: bool
    auth_provider: str
    created_at: datetime
    updated_at: datetime
