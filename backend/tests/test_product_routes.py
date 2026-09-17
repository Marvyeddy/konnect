import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from fastapi import HTTPException, status
import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_user
from backend.main import app
from backend.models.products import Product
from backend.models.users import Users
from backend.routers.products import admin_vendor_role

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

    app.dependency_overrides[admin_vendor_role] = lambda: True
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

    app.dependency_overrides[admin_vendor_role] = raise_forbidden
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

    response = await client.post("/api/v1/products", data=data, files=files)

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

    mock_cloudinary.side_effect = [{"secure_url": "https://mocked.cloudinary"}]

    update_payload = {}
    data = {"product_data": json.dumps(update_payload)}
    files = [("images", ("patched_view.jpg", b"new-binary-bytes", "image/jpeg"))]

    response = await client.patch(
        f"/api/v1/products/{existing_product.id}", data=data, files=files
    )

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["images"] == ["https://mocked.cloudinary"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_vendor_auth")
async def test_edit_product_not_found_or_unauthorized(client):
    random_product_id = uuid.uuid4()
    update_payload = {"name": "Hacked Name Change"}
    data = {"product_data": json.dumps(update_payload)}

    response = await client.patch(f"/api/v1/products/{random_product_id}", data=data)

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

    response = await client.patch(f"/api/v1/products/{existing_product.id}", data=data)

    assert response.status_code == 400
    assert "No fields provided for updates" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_vendor_auth")
async def test_delete_product_by_owner_vendor_success(client, session):
    product = Product(
        id=PRODUCT_ID,
        vendor_id=TEST_VENDOR_ID,
        name="Vendor Item",
        description="To be deleted by owner",
        price=15.00,
        discount=0,
        in_stock=True,
        images=[],
        category="Tech",
    )
    session.add(product)
    await session.commit()

    response = await client.delete(f"/api/v1/products/{product.id}")

    assert response.status_code == 200
    assert response.json() == {"detail": "Product deleted successfully."}


@pytest.fixture
def mock_admin_auth():
    admin = MagicMock()
    admin.id = uuid.uuid4()
    admin.role = "admin"

    app.dependency_overrides[admin_vendor_role] = lambda: True
    app.dependency_overrides[get_current_user] = lambda: admin

    yield admin

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch(
    "backend.routers.products.product_service.delete_product", new_callable=AsyncMock
)
async def test_delete_product_by_admin_success(
    mock_delete_product, client, session, mock_admin_auth
):
    mock_delete_product.return_value = True

    fake_product_id = uuid.uuid4()

    response = await client.delete(f"/api/v1/products/{fake_product_id}")

    assert response.status_code == 200
    assert response.json() == {"detail": "Product deleted successfully."}

    mock_delete_product.assert_called_once_with(
        product_id=fake_product_id,
        vendor_id=None,
        session=session,
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_vendor_auth")
async def test_delete_product_unauthorized_or_not_found(client, session):
    stranger_vendor = Users(
        id=uuid.uuid4(),
        email="unauthorized_vendor@gmail.com",
        password="securepassword123",
        username="stranger_vendor_username",
        role="vendor",
    )
    session.add(stranger_vendor)
    await session.commit()

    target_product_id = uuid.uuid4()
    product = Product(
        id=target_product_id,
        vendor_id=stranger_vendor.id,
        name="Private Item",
        description="Belongs to someone else",
        price=45.00,
        discount=0,
        in_stock=True,
        images=[],
        category="Tech",
    )
    session.add(product)
    await session.commit()

    response = await client.delete(f"/api/v1/products/{target_product_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found or unauthorized."
