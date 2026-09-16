import asyncio
import json
from unittest.mock import patch
import uuid
from fastapi import HTTPException, status
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_user
from backend.main import app
from backend.models.products import Product
from backend.models.users import Users
from backend.routers.products import vendor_role

PRODUCT_ID = uuid.uuid4()
TEST_VENDOR_ID = uuid.uuid4()


@pytest.fixture
def mock_vendor_auth(session):
    vendor_user = Users(
        id=TEST_VENDOR_ID,
        email="vendor_owner@gmail.com",
        password="securepassword123",
        username="onboarding_vendor",
        role="vendor",
    )

    async def _async_setup():
        session.add(vendor_user)
        await session.commit()
        await session.refresh(vendor_user)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_async_setup())

    app.dependency_overrides[vendor_role] = lambda: True
    app.dependency_overrides[get_current_user] = lambda: vendor_user

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def mock_unauthorized_auth():
    def raise_forbidden():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    app.dependency_overrides[vendor_role] = raise_forbidden
    yield
    app.dependency_overrides.clear()


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


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_vendor_auth")
@patch("backend.routers.products.cloudinary.uploader.upload")
async def test_product_success_all_files(mock_cloudinary, client):
    mock_cloudinary.side_effect = [
        {"secure_url": "https://mocked.cloudinary"},
        {"secure_url": "https://mocked.cloudinary"},
    ]

    product_data = {
        "name": "Shiny Widget",
        "description": "The best widget around.",
        "category": "Gadgets",
        "price": 88.88,
        "discount": 25,
        "in_stock": True,
    }

    data = {"product_data": json.dumps(product_data)}
    files = [
        ("images", ("product1.jpg", b"imagedata1", "image/jpeg")),
        ("images", ("product2.png", b"imagedata2", "image/png")),
    ]

    # Act
    response = await client.post("/api/v1/products", data=data, files=files)

    # Assert
    assert response.status_code == 201
    res_json = response.json()
    assert res_json["name"] == "Shiny Widget"
    assert res_json["images"] == [
        "https://mocked.cloudinary",
        "https://mocked.cloudinary",
    ]


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_vendor_auth")
async def test_edit_product_partial_success(client, session):
    existing_product = Product(
        id=PRODUCT_ID,
        vendor_id=TEST_VENDOR_ID,
        name="Original Gadget",
        description="Old description",
        price=100.00,
        discount=10,
        in_stock=True,
        images=["https://mocked.cloudinary"],
        category="Tech",
    )
    session.add(existing_product)
    await session.commit()
    await session.refresh(existing_product)

    update_payload = {"price": 149.99}
    data = {"product_data": json.dumps(update_payload)}

    response = await client.patch(f"/api/v1/products/{existing_product.id}", data=data)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["price"] == 149.99
    assert res_json["name"] == "Original Gadget"
    assert res_json["in_stock"] is True


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_vendor_auth")
@patch("backend.routers.products.cloudinary.uploader.upload")
async def test_edit_product_with_new_images(mock_cloudinary, client, session):
    existing_product = Product(
        id=PRODUCT_ID,
        vendor_id=TEST_VENDOR_ID,
        name="Image Test Unit",
        description="Desc",
        price=50.00,
        discount=0,
        in_stock=True,
        images=[],
        category="Tech",
    )
    session.add(existing_product)
    await session.commit()
    await session.refresh(existing_product)

    # Cloudinary setup responses
    mock_cloudinary.side_effect = [{"secure_url": "https://mocked.cloudinary"}]

    update_payload = {}
    data = {"product_data": json.dumps(update_payload)}
    files = [("images", ("patched_view.jpg", b"new-binary-bytes", "image/jpeg"))]

    # 2. Act
    response = await client.patch(
        f"/api/v1/products/{existing_product.id}", data=data, files=files
    )

    # 3. Assert
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["images"] == ["https://mocked.cloudinary"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_vendor_auth")
async def test_edit_product_not_found_or_unauthorized(client):
    random_product_id = uuid.uuid4()
    update_payload = {"name": "Hacked Name Change"}
    data = {"product_data": json.dumps(update_payload)}

    # 2. Act
    response = await client.patch(f"/api/v1/products/{random_product_id}", data=data)

    # 3. Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found or not authorized"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_vendor_auth")
async def test_edit_product_no_fields_provided(client, session):
    existing_product = Product(
        id=PRODUCT_ID,
        vendor_id=TEST_VENDOR_ID,
        name="Stagnant Product",
        description="No alterations",
        price=20.00,
        discount=0,
        in_stock=True,
        images=[],
        category="Tech",
    )
    session.add(existing_product)
    await session.commit()
    await session.refresh(existing_product)

    data = {"product_data": json.dumps({})}

    # 2. Act
    response = await client.patch(f"/api/v1/products/{existing_product.id}", data=data)

    # 3. Assert
    assert response.status_code == 400
    assert "No fields provided for updates" in response.json()["detail"]
