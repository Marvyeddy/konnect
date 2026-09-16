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

    async def create_product(
        self,
        vendor_id: uuid.UUID,
        product_data,
        images: list[str],
        session: AsyncSession,
    ):
        new_product = Product(
            vendor_id=vendor_id,
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            discount=product_data.discount,
            in_stock=product_data.in_stock,
            images=images,
            category=product_data.category,
        )
        session.add(new_product)
        await session.commit()
        await session.refresh(new_product)
        return new_product

    async def get_product_by_id_and_vendor(
        self, product_id: uuid.UUID, vendor_id: uuid.UUID, session: AsyncSession
    ):
        statement = select(Product).where(
            Product.id == product_id,
            Product.vendor_id == vendor_id,
        )
        result = await session.execute(statement)
        product = result.scalar_one_or_none()
        return product

    async def update_product(
        self,
        product_id: uuid.UUID,
        vendor_id: uuid.UUID,
        product_data: dict,
        images: list[str] | None,
        session: AsyncSession,
    ):
        product = await self.get_product_by_id_and_vendor(
            product_id, vendor_id, session
        )
        if not product:
            return None

        for field in [
            "name",
            "description",
            "price",
            "discount",
            "in_stock",
            "category",
        ]:
            if field in product_data:
                setattr(product, field, product_data[field])

        if images is not None:
            product.images = images

        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product
