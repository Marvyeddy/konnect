from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from backend.constants.main import PermissionLevel, Roles


class UserProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    image: str | None = None
    permission_level: PermissionLevel | None = None
    created_at: datetime
    updated_at: datetime


class VendorProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    image: str | None = None
    business_licence: str | None = None
    phone_number: str
    rating: float
    report_count: int
    verified: bool
    address: str
    business_name: str
    created_at: datetime
    updated_at: datetime


class UserOut(BaseModel):
    id: UUID
    email: str
    username: str
    google_id: Optional[str] = None
    role: Roles
    auth_provider: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    user_profile: UserProfileOut | None = None
    vendor_profile: VendorProfileOut | None = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
