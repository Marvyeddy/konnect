from datetime import UTC, datetime
from typing import TYPE_CHECKING
import uuid

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import (
    CheckConstraint,
    Column,
    Field,
    Relationship,
    SQLModel,
    UniqueConstraint,
)

if TYPE_CHECKING:
    from backend.models.users import Users
    from backend.models.vendor_profile import VendorProfile


class VendorReview(SQLModel, table=True):
    __tablename__ = "vendor_review"
    __table_args__ = (
        UniqueConstraint("buyer_id", "vendor_id", name="uq_review_buyer_vendor"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    buyer_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    vendor_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            sa.ForeignKey("vendor_profile.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    rating: int = Field(
        sa_column=Column(
            pg.INTEGER,
            nullable=False,
        )
    )
    comment: str | None = Field(
        default=None,
        sa_column=Column(
            pg.TEXT,
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    buyer: "Users" = Relationship(back_populates="reviews_written")
    vendor: "VendorProfile" = Relationship(back_populates="reviews")

    def __repr__(self):
        return (
            f"<Review(id={self.id}, buyer_id={self.buyer_id}, vendor_id={self.vendor_id}, "
            f"rating={self.rating}, comment={self.comment!r}, created_at={self.created_at})>"
        )
