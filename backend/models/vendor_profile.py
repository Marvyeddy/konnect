import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.users import Users


class VendorProfile(SQLModel, table=True):
    __tablename__ = "vendor_profile"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        )
    )
    full_name: str = Field(
        sa_column=Column(
            pg.TEXT,
            nullable=False,
        )
    )
    image: str | None = Field(
        default=None,
        sa_column=Column(
            pg.TEXT,
            nullable=True,
        ),
    )
    business_licence: str | None = Field(
        default=None,
        sa_column=Column(
            pg.TEXT,
            nullable=True,
        ),
    )
    phone_number: str = Field(
        sa_column=Column(
            pg.TEXT,
            nullable=False,
        ),
    )
    rating: float = Field(
        default=3.0,
        sa_column=Column(
            pg.FLOAT,
            nullable=False,
            server_default=sa.text("3.0"),
        ),
    )
    report_count: int = Field(
        default=0,
        sa_column=Column(pg.INTEGER, nullable=False, server_default=sa.text("0")),
    )
    verified: bool = Field(
        default=False,
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default=sa.false()),
    )
    address: str = Field(
        sa_column=Column(
            pg.VARCHAR(255),
            nullable=False,
        )
    )
    business_name: str = Field(
        sa_column=Column(
            pg.TEXT,
            nullable=False,
        )
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    user: "Users" = Relationship(back_populates="vendor_profile")

    def __repr__(self):
        return (
            f"<VendorProfile(id={self.id}, user_id={self.user_id}, "
            f"business_name={self.business_name!r}, "
            f"address={self.address!r}, "
            f"rating={self.rating}, verified={self.verified}, "
            f"report_count={self.report_count}, "
            f"created_at={self.created_at}, updated_at={self.updated_at})>"
        )
