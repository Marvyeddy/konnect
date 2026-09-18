from datetime import UTC, datetime
from typing import TYPE_CHECKING
import uuid
from sqlmodel import Column, Field, Relationship, SQLModel
import sqlalchemy.dialects.postgresql as pg
import sqlalchemy as sa

from backend.constants.main import ReportStatus

if TYPE_CHECKING:
    from backend.models.users import Users
    from backend.models.vendor_profile import VendorProfile


class VendorReport(SQLModel, table=True):
    __tablename__ = "vendor_report"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    reporter_id: uuid.UUID = Field(
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
    reason: str = Field(
        sa_column=Column(
            pg.TEXT,
            nullable=False,
        )
    )
    status: ReportStatus | str = Field(
        default=ReportStatus.PENDING,
        sa_column=Column(
            pg.TEXT,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    reporter: "Users" = Relationship(back_populates="reports_submitted")
    vendor: "VendorProfile" = Relationship(back_populates="reports")

    def __repr__(self):
        return (
            f"<Report(id={self.id}, reporter_id={self.reporter_id}, vendor_id={self.vendor_id}, "
            f"reason={self.reason!r}, status={self.status}, "
            f"created_at={self.created_at})>"
        )
