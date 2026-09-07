from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from backend.constants.main import Roles


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
    google_id: str | None = None
    role: Roles
    auth_provider: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    vendor_profile: VendorProfileOut | None = None


class VendorUpdate(BaseModel):
    username: str
    password: str
