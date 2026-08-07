import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import Column, Field, SQLModel


class Users(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    email: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=False, unique=True))
    password: str = Field(sa_column=Column(pg.VARCHAR, nullable=True))
    role: str = Field(
        default="user", sa_column=Column(pg.TEXT, nullable=False, server_default="user")
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default=sa.text("true")),
    )
    google_id: str | None = Field(
        default=None,
        sa_column=Column(pg.VARCHAR, index=True, unique=True, nullable=True),
    )
    auth_provider: str = Field(
        default="local",
        sa_column=Column(pg.TEXT, nullable=False, server_default="local"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            server_onupdate=sa.FetchedValue(),
        ),
    )

    def __repr__(self):
        return f"<User email: {self.email}>"
