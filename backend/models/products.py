import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Column, Field, Relationship, SQLModel
import sqlalchemy.dialects.postgresql as pg
import sqlalchemy as sa

if TYPE_CHECKING:
    from backend.models.users import Users


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )

    vendor_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    name: str = Field(
        sa_column=Column(
            pg.TEXT,
            nullable=False,
        )
    )
    description: str = Field(sa_column=Column(pg.TEXT, nullable=False))
    price: float = Field(sa_column=Column(pg.FLOAT, nullable=False))
    discount: int = Field(
        default=0,
        sa_column=Column(pg.INTEGER, nullable=False, server_default=sa.text("0")),
    )
    in_stock: bool = Field(
        default=True,
        sa_column=Column(pg.BOOLEAN, nullable=False, server_default=sa.true()),
    )
    images: Optional[list[str]] = Field(
        default=None, sa_column=Column(pg.ARRAY(pg.TEXT), nullable=True)
    )
    category: str = Field(sa_column=Column(pg.TEXT, nullable=False))

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

    user: "Users" = Relationship(back_populates="products")

    def __repr__(self):
        return (
            f"<Product(id={self.id}, name={self.name!r}, price={self.price}, "
            f"discount={self.discount}, in_stock={self.in_stock}, "
            f"category={self.category!r}, vendor_id={self.vendor_id}, "
            f"created_at={self.created_at}, updated_at={self.updated_at})>"
        )
