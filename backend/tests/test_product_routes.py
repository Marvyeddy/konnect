import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.products import Product
from backend.models.users import Users

PRODUCT_ID = uuid.uuid4()


@pytest.mark.asyncio
async def test_get_products(client, session: AsyncSession):
    vendor = Users(
        id=uuid.uuid4(),
        email="vendor@email.com",
        username="vendor_username",
        password="hashed_password",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    product = Product(
        id=PRODUCT_ID,
        vendor_id=vendor.id,
        name="product1",
        description="product1 description",
        price=30.00,
        discount=20,
        in_stock=False,
        images=None,
        category="Tech",
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)

    response = await client.get("/api/v1/products")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(PRODUCT_ID)
    assert data[0]["name"] == "product1"
    assert data[0]["description"] == "product1 description"
    assert data[0]["price"] == 30.00
    assert data[0]["discount"] == 20
    assert data[0]["in_stock"] is False
    assert data[0]["category"] == "Tech"
    assert data[0]["vendor_id"] == str(vendor.id)


@pytest.mark.asyncio
async def test_get_products_not_found(client):
    response = await client.get("/api/v1/products")

    assert response.status_code == 404

    assert response.json() == {
        "message": "Products are not available",
        "error": "product_unavailable",
    }


@pytest.mark.asyncio
async def test_get_products_by_vendor(client, session: AsyncSession):
    vendor = Users(
        id=uuid.uuid4(),
        email="vendor@email.com",
        username="vendor_username",
        password="hashed_password",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    product = Product(
        id=PRODUCT_ID,
        vendor_id=vendor.id,
        name="product1",
        description="product1 description",
        price=30.00,
        discount=20,
        in_stock=False,
        images=None,
        category="Tech",
    )

    session.add(product)
    await session.commit()
    await session.refresh(product)

    response = await client.get(f"/api/v1/products/vendor/{vendor.id}")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(PRODUCT_ID)
    assert data[0]["name"] == "product1"
    assert data[0]["description"] == "product1 description"
    assert data[0]["price"] == 30.00
    assert data[0]["discount"] == 20
    assert data[0]["in_stock"] is False
    assert data[0]["category"] == "Tech"
    assert data[0]["vendor_id"] == str(vendor.id)


@pytest.mark.asyncio
async def test_get_products_by_vendor_not_found(client):
    FALSE_ID = uuid.uuid4()
    response = await client.get(f"/api/v1/products/vendor/{FALSE_ID}")

    assert response.status_code == 404

    assert response.json() == {
        "detail": f"No products found for vendor ID {FALSE_ID}",
    }


@pytest.mark.asyncio
async def test_get_product(client, session):
    vendor = Users(
        id=uuid.uuid4(),
        email="vendor@email.com",
        username="vendor_username",
        password="hashed_password",
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    product = Product(
        id=PRODUCT_ID,
        vendor_id=vendor.id,
        name="product1",
        description="product1 description",
        price=30.00,
        discount=20,
        in_stock=False,
        images=None,
        category="Tech",
    )

    session.add(product)
    await session.commit()
    await session.refresh(product)

    response = await client.get(f"/api/v1/products/{PRODUCT_ID}")

    assert response.status_code == 200

    assert response.json()["name"] == "product1"


@pytest.mark.asyncio
async def test_get_product_not_found(client):
    response = await client.get(f"/api/v1/products/{PRODUCT_ID}")

    assert response.status_code == 404

    assert response.json() == {
        "detail": f"No products found for product ID {PRODUCT_ID}"
    }
