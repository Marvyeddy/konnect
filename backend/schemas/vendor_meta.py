from pydantic import BaseModel, Field
from typing import Optional


class ReviewCreate(BaseModel):
    rating: int = Field(
        ..., ge=1, le=5, description="Rating must be between 1 and 5 stars"
    )
    comment: Optional[str] = Field(
        None, max_length=1000, description="Optional review text"
    )


class ReportCreate(BaseModel):
    reason: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed explanation of the report reason",
    )
