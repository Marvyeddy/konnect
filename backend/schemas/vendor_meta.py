from datetime import datetime
import uuid
from pydantic import BaseModel, Field

from backend.constants.main import ReportStatus


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewRead(BaseModel):
    id: uuid.UUID
    buyer_id: uuid.UUID
    vendor_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    reason: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed explanation of the report reason",
    )


class ReportRead(BaseModel):
    id: uuid.UUID
    reporter_id: uuid.UUID
    vendor_id: uuid.UUID
    reason: str
    status: ReportStatus
    reviewed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ReportReview(BaseModel):
    status: ReportStatus
