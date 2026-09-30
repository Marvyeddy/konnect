import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cloudinary.exceptions import BadRequest
from fastapi import status

from backend.dependencies import get_current_user, get_rabbit
from backend.main import app
from backend.models.users import Users

MOCK_USER_ID = uuid.uuid4()


@pytest.fixture(autouse=True, scope="function")
def mock_onboarding_auth_globally():
    """Globally overrides user authentication for onboarding integration tests."""
    mock_user = MagicMock()
    mock_user.id = MOCK_USER_ID
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.clear()


# ============================================================================
# 1. SUCCESS PATHS
# ============================================================================


@pytest.mark.asyncio
@patch(
    "backend.routers.onboarding._upload_to_cloudinary"
)  # 1. Patch the local helper function
async def test_onboard_user_success_with_image(mock_upload, client, session):
    """Test onboarding completes successfully when a valid image file is uploaded."""

    # Seed matching user row using a valid native UUID object
    parent_user = Users(
        id=MOCK_USER_ID,
        email="onboarding_owner@gmail.com",
        username="onboarding_owner",
        password="securepassword123",
        role="user",
    )
    session.add(parent_user)
    await session.commit()
    await session.refresh(parent_user)

    # 2. Mock the async helper function return value directly
    mock_upload.return_value = "https://cloudinary.com"

    data = {"full_name": "Marvelous Tester"}
    files = {"image": ("profile.png", b"fake_binary_png_stream_content", "image/png")}

    response = await client.post("/api/v1/onboarding/user", data=data, files=files)

    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()
    assert res_data["message"] == "User onboarded successfully"

    from backend.models.user_profile import UserProfile
    import sqlalchemy as sa

    result = await session.execute(
        sa.select(UserProfile).where(UserProfile.user_id == MOCK_USER_ID)
    )
    db_profile = result.scalar_one_or_none()

    assert db_profile is not None
    assert db_profile.full_name == "Marvelous Tester"
    assert db_profile.image == "https://cloudinary.com"


@pytest.mark.asyncio
@patch("backend.routers.onboarding._upload_to_cloudinary")
async def test_onboard_user_success_without_image(mock_upload, client, session):
    """Test onboarding passes cleanly when no profile image asset is provided."""
    parent_user = Users(
        id=MOCK_USER_ID,
        email="onboarding_no_image@gmail.com",
        username="onboarding_no_image",
        password="securepassword123",
        role="user",
    )
    session.add(parent_user)
    await session.commit()
    await session.refresh(parent_user)

    data = {"full_name": "No Image User"}
    response = await client.post("/api/v1/onboarding/user", data=data)

    assert response.status_code == status.HTTP_200_OK

    from backend.models.user_profile import UserProfile
    import sqlalchemy as sa

    result = await session.execute(
        sa.select(UserProfile).where(UserProfile.user_id == MOCK_USER_ID)
    )
    db_profile = result.scalar_one_or_none()

    assert db_profile is not None
    assert db_profile.full_name == "No Image User"
    assert db_profile.image is None

    mock_upload.assert_not_called()


# ============================================================================
# 2. VALIDATION & FAILURE PATHS
# ============================================================================


@pytest.mark.asyncio
async def test_onboard_user_fail_invalid_file_extension(client):
    data = {"full_name": "Hacker Doe"}
    files = {"image": ("malicious.sh", b"echo 'harmful'", "image/png")}
    response = await client.post("/api/v1/onboarding/user", data=data, files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid file extension"


@pytest.mark.asyncio
async def test_onboard_user_fail_invalid_content_type(client):
    data = {"full_name": "Jane Doe"}
    files = {"image": ("avatar.jpg", b"fake_jpg", "text/plain")}
    response = await client.post("/api/v1/onboarding/user", data=data, files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid file content type"


@pytest.mark.asyncio
async def test_onboard_user_fail_file_size_exceeded(client):
    data = {"full_name": "Heavy Image User"}
    large_byte_stream = b"0" * (11 * 1024 * 1024)
    files = {"image": ("giant.png", large_byte_stream, "image/png")}
    response = await client.post("/api/v1/onboarding/user", data=data, files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "File size is too large (Max 10MB)"


@pytest.mark.asyncio
@patch("backend.routers.onboarding._upload_to_cloudinary")
async def test_onboard_user_fail_cloudinary_exception(mock_upload, client, session):
    parent_user = Users(
        id=MOCK_USER_ID,
        email="onboarding_failed_upload@gmail.com",
        username="onboarding_failed_upload",
        password="securepassword123",
        role="user",
    )
    session.add(parent_user)
    await session.commit()
    await session.refresh(parent_user)

    mock_upload.side_effect = BadRequest("Connection reset by cloud peer")

    data = {"full_name": "Unfortunate User"}
    files = {"image": ("avatar.jpg", b"jpeg_bytes", "image/jpeg")}

    response = await client.post("/api/v1/onboarding/user", data=data, files=files)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Cloudinary upload failed" in response.json()["detail"]


# ============================================================================
# 1. SUCCESS PATHS
# ============================================================================


@pytest.mark.asyncio
@patch(
    "backend.routers.onboarding.auth_service.update_user"
)  # 1. Patch auth_service if needed
@patch("backend.routers.onboarding._upload_to_cloudinary")
async def test_onboard_vendor_success_no_optional_image(
    mock_upload, mock_update_user, client, session
):
    """Test onboarding passes when the optional profile image payload is missing."""

    # Seed matching user row using a valid native UUID object
    parent_user = Users(
        id=MOCK_USER_ID,
        email="vendor_no_img@gmail.com",
        password="securepassword123",
        username="onboarding_vendor",
        role="user",
    )
    session.add(parent_user)
    await session.commit()
    await session.refresh(parent_user)

    # 2. Correct the mock value structure to return a string directly (what your route reads)
    mock_upload.return_value = "https://cloudinary.com"
    mock_update_user.return_value = None

    mock_rabbit = AsyncMock()
    app.dependency_overrides[get_rabbit] = lambda: mock_rabbit

    data = {
        "vendor_data": json.dumps(
            {
                "full_name": "Marvelous Tech Solutions",
                "phone_number": "+2348012345678",
                "address": "123 Innovation Drive",
                "business_name": "Ginger Block",
            }
        )
    }

    # Provide only the strictly required license file parameter
    files = {"business_license": ("license.jpg", b"fake_jpeg_data", "image/jpeg")}

    try:
        response = await client.post(
            "/api/v1/onboarding/vendor", data=data, files=files
        )

        # 4. Assertions match the actual return signature of your route
        assert response.status_code == status.HTTP_200_OK
        res_payload = response.json()
        assert res_payload["image_url"] is None
        assert res_payload["license_url"] == "https://cloudinary.com"

        # Verify message broker broadcast was called correctly
        mock_rabbit.publish.assert_called_once()

    finally:
        # Always clean up dependency overrides to protect subsequent tests
        app.dependency_overrides.clear()


# ============================================================================
# 2. VALIDATION & FAILURE PATHS
# ============================================================================


@pytest.mark.asyncio
async def test_onboard_vendor_fail_invalid_json_payload(client):
    app.state.rabbit = MagicMock()

    data = {"vendor_data": "corrupt_non_json_string_value_here"}
    files = {"business_license": ("license.png", b"data", "image/png")}

    try:
        response = await client.post(
            "/api/v1/onboarding/vendor", data=data, files=files
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    finally:
        delattr(app.state, "rabbit")


@pytest.mark.asyncio
async def test_onboard_vendor_fail_invalid_image_extension(client):
    """Verify endpoint validation filters bad image file extensions."""
    app.state.rabbit = MagicMock()
    data = {
        "vendor_data": json.dumps(
            {
                "full_name": "Marvelous Tech Solutions",
                "phone_number": "+2348012345678",
                "address": "123 Innovation Drive",
                "business_name": "Ginger Block",
            }
        )
    }
    files = {
        "image": ("profile.sh", b"harmful script", "image/png"),
        "business_license": ("license.png", b"license_bytes", "image/png"),
    }

    try:
        response = await client.post(
            "/api/v1/onboarding/vendor", data=data, files=files
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid image file extension"
    finally:
        delattr(app.state, "rabbit")


@pytest.mark.asyncio
async def test_onboard_vendor_fail_license_size_exceeded(client):
    """Verify endpoint drops license uploads breaking the 15MB file ceiling constraint."""
    app.state.rabbit = MagicMock()
    data = {
        "vendor_data": json.dumps(
            {
                "full_name": "Marvelous Tech Solutions",
                "phone_number": "+2348012345678",
                "address": "123 Innovation Drive",
                "business_name": "Ginger Block",
            }
        )
    }

    # Generate an over-allocated file stream payload mapping to 16 megabytes
    huge_payload = b"0" * (16 * 1024 * 1024)
    files = {"business_license": ("massive_doc.pdf", huge_payload, "application/pdf")}

    try:
        response = await client.post(
            "/api/v1/onboarding/vendor", data=data, files=files
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Business license size is too large" in response.json()["detail"]
    finally:
        delattr(app.state, "rabbit")
