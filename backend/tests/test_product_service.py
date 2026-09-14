import uuid
import pytest

from backend.models.products import Product
from backend.models.users import Users  # 👈 Import your Users model
from backend.services.product import ProductService

PRODUCT_ID = uuid.uuid4()
product_service = ProductService()


@pytest.mark.asyncio
async def test_get_all_products(session):
    vendor = Users(
        email="vendor@example.com",
        password="hashed-password",
        username="testvendor",
        role="vendor",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    seeded_data = Product(
        id=PRODUCT_ID,
        vendor_id=vendor.id,
        name="product 1",
        description="product1 description",
        price=30.00,
        category="tech",
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    # 3. Fetch and assert
    products = await product_service.get_all_products(session)

    assert products is not None
    assert len(products) > 0
    assert products[0].discount == 0
    assert products[0].category == "tech"


@pytest.mark.asyncio
async def test_get_product_by_id(session):
    vendor = Users(
        email="vendor@example.com",
        password="hashed-password",
        username="testvendor",
        role="vendor",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    seeded_data = Product(
        id=PRODUCT_ID,
        vendor_id=vendor.id,
        name="product 1",
        description="product1 description",
        price=30.00,
        category="tech",
        discount=30,
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    product = await product_service.get_product(seeded_data.id, session)

    assert product is not None
    assert product.discount == 30


@pytest.mark.asyncio
async def test_get_products_by_vendor_id(session):
    vendor = Users(
        email="vendor@example.com",
        password="hashed-password",
        username="testvendor",
        role="vendor",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    seeded_data = Product(
        id=PRODUCT_ID,
        vendor_id=vendor.id,
        name="product 1",
        description="product1 description",
        price=30.00,
        category="stationary",
        discount=30,
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    products = await product_service.get_products_by_vendor_id(
        seeded_data.vendor_id, session
    )

    assert len(products) > 0
    assert products[0].discount == 30
    assert products[0].category == "stationary"
