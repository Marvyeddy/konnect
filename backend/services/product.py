from datetime import datetime
from typing import List
import uuid
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.products import Product


class ProductService:
    async def get_all_products(
        self,
        session: AsyncSession,
        limit: int = 20,
        created_at_cursor: str = None,
        id_cursor: str = None,
        search: str = None,
    ) -> List[Product]:
        statement = select(Product).order_by(desc(Product.created_at), desc(Product.id))

        if search:
            search_query = f"%{search}%"
            statement = statement.where(
                or_(
                    Product.name.ilike(search_query),
                    Product.description.ilike(search_query),
                    Product.category.ilike(search_query),
                )
            )

        if created_at_cursor and id_cursor:
            statement = statement.where(
                or_(
                    Product.created_at < datetime.fromisoformat(created_at_cursor),
                    or_(
                        Product.created_at == datetime.fromisoformat(created_at_cursor),
                        Product.id < uuid.UUID(id_cursor),
                    ),
                )
            )

        statement = statement.limit(limit)
        result = await session.execute(statement)
        products = result.scalars().all()
        return products

    async def get_product(self, id: uuid.UUID, session: AsyncSession):
        statement = select(Product).where(Product.id == id)
        result = await session.execute(statement)
        product = result.scalar_one_or_none()
        return product

    async def get_products_by_vendor_id(
        self,
        vendor_id: uuid.UUID,
        session: AsyncSession,
        limit: int = 20,
        created_at_cursor: str = None,
        id_cursor: str = None,
        search: str = None,
    ) -> List[Product]:
        statement = (
            select(Product)
            .where(Product.vendor_id == vendor_id)
            .order_by(desc(Product.created_at), desc(Product.id))
        )

        if search:
            search_query = f"%{search}%"
            statement = statement.where(
                or_(
                    Product.name.ilike(search_query),
                    Product.description.ilike(search_query),
                    Product.category.ilike(search_query),
                )
            )

        if created_at_cursor and id_cursor:
            statement = statement.where(
                or_(
                    Product.created_at < datetime.fromisoformat(created_at_cursor),
                    or_(
                        Product.created_at == datetime.fromisoformat(created_at_cursor),
                        Product.id < uuid.UUID(id_cursor),
                    ),
                )
            )

        statement = statement.limit(limit)
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

    async def delete_product(
        self,
        product_id: uuid.UUID | None,
        vendor_id: uuid.UUID | None,
        session: AsyncSession,
    ):
        product = await self.get_product_by_id_and_vendor(
            product_id, vendor_id, session
        )
        if not product:
            return False

        await session.delete(product)
        await session.commit()
        return True
