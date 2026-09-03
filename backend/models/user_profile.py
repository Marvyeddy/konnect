import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.users import Users

from backend.constants.main import PermissionLevel


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profile"

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
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,  # Typically, foreign keys like user_id are indexed for join efficiency
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
    permission_level: PermissionLevel | None = Field(
        default=None,
        sa_column=Column(
            pg.TEXT,
            nullable=True,
            index=True,  # Useful to index if you filter on this for admin views/lists
        ),
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
    user: "Users" = Relationship(back_populates="user_profile")

    def __repr__(self):
        return f"<UserProfile user_id: {self.user_id}, full_name: {self.full_name}>"
