import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.users import Users


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

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
            index=True,
        )
    )
    title: str = Field(sa_column=Column(pg.VARCHAR(100), nullable=False))
    message: str = Field(sa_column=Column(pg.TEXT, nullable=False))
    notification_type: str = Field(
        default="INFO",
        sa_column=Column(pg.TEXT, server_default=sa.text("'INFO'")),
    )
    action_url: str | None = Field(sa_column=Column(pg.VARCHAR(255), nullable=True))
    is_read: bool = Field(
        default=False,
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default=sa.false()),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    user: "Users" = Relationship(back_populates="notifications")
