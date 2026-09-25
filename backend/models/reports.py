from datetime import UTC, datetime
from typing import TYPE_CHECKING
import uuid

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import Column, Field, Relationship, SQLModel, UniqueConstraint

from backend.constants.main import ReportStatus

if TYPE_CHECKING:
    from backend.models.users import Users
    from backend.models.vendor_profile import VendorProfile


def _report_status_values(enum_cls):
    return [m.value for m in enum_cls]


class VendorReport(SQLModel, table=True):
    __tablename__ = "vendor_report"
    __table_args__ = (
        # One report per user per vendor — neutralizes report spam/brigading.
        UniqueConstraint("reporter_id", "vendor_id", name="uq_report_reporter_vendor"),
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
    status: ReportStatus = Field(
        default=ReportStatus.PENDING,
        sa_column=Column(
            pg.ENUM(
                ReportStatus,
                name="report_status",
                create_type=True,
                values_callable=_report_status_values,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    reviewed_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=True,
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
