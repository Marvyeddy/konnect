import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import Column, Field, SQLModel

from backend.constants.main import Roles


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
    email: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=False, index=True))
    password: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=True))
    username: str = Field(sa_column=Column(pg.VARCHAR(255), nullable=False))
    role: Roles = Field(
        default=Roles.USER,
        sa_column=Column(
            pg.TEXT, nullable=False, index=True, server_default=sa.text("'user'")
        ),
    )
    google_id: str | None = Field(
        default=None,
        sa_column=Column(
            pg.TEXT,
            nullable=True,
            unique=True,
            index=True,
        ),
    )
    auth_provider: str = Field(
        default="local",
        sa_column=Column(pg.TEXT, nullable=False, server_default=sa.text("'local'")),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default=sa.true()),
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

    def __repr__(self):
        return f"<User email: {self.email} & username: {self.username}>"
