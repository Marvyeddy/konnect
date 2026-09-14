from typing import List
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.products import Product


class ProductService:
    async def get_all_products(self, session: AsyncSession) -> List[Product]:
        statement = select(Product).order_by(desc(Product.created_at))
        result = await session.execute(statement)
        products = result.scalars().all()
        return products

    async def get_product(self, id: uuid.UUID, session: AsyncSession):
        statement = select(Product).where(Product.id == id)
        result = await session.execute(statement)
        product = result.scalar_one_or_none()
        return product

    async def get_products_by_vendor_id(
        self, vendor_id: uuid.UUID, session: AsyncSession
    ):
        statement = (
            select(Product)
            .where(Product.vendor_id == vendor_id)
            .order_by(desc(Product.created_at))
        )
        result = await session.execute(statement)
        products = result.scalars().all()
        return products
