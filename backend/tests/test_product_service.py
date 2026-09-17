import uuid
import pytest

from backend.models.products import Product
from backend.models.users import Users  # 👈 Import your Users model
from backend.services.product import ProductService

PRODUCT_ID = uuid.uuid4()
product_service = ProductService()


@pytest.mark.asyncio
async def test_get_all_products(session):
    # 1. Arrange: Create and insert a valid vendor row to satisfy foreign keys
    vendor = Users(
        id=uuid.uuid4(),
        email="vendor@example.com",
        password="hashed-password",
        username="testvendor",
        role="vendor",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    # 2. Arrange: Create and insert the product linked to the active vendor
    seeded_data = Product(
        id=PRODUCT_ID,
        vendor_id=vendor.id,
        name="product 1",
        description="product1 description",
        price=30.00,
        discount=0,
        in_stock=True,
        images=[],
        category="tech",
    )
    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    # 3. Act: Invoke the refactored paginated service layer method
    products = await product_service.get_all_products(
        session=session, limit=20, created_at_cursor=None, id_cursor=None, search=None
    )

    # 4. Assert: Validate the list structures and fields match perfectly
    assert products is not None
    assert isinstance(products, list)
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
    # 1. Arrange: Create and insert a valid vendor row
    vendor = Users(
        id=uuid.uuid4(),
        email="vendor@example.com",
        password="hashed-password",
        username="testvendor",
        role="vendor",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    # 2. Arrange: Create and insert the product linked to this vendor
    seeded_data = Product(
        id=PRODUCT_ID,
        vendor_id=vendor.id,
        name="product 1",
        description="product1 description",
        price=30.00,
        category="stationary",
        discount=30,
        in_stock=True,
        images=[],
    )
    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    # 3. Act: Call the service layer passing the updated signature fields
    products = await product_service.get_products_by_vendor_id(
        vendor_id=seeded_data.vendor_id,
        session=session,
        limit=20,  # Added default limit
        created_at_cursor=None,  # Added empty cursor position
        id_cursor=None,  # Added empty cursor ID fallback
        search=None,  # Added empty search filter text
    )

    # 4. Assert: Validate the list state matches your original conditions
    assert isinstance(products, list)
    assert len(products) > 0
    assert products[0].discount == 30
    assert products[0].category == "stationary"
