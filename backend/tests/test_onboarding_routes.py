import json
import uuid
from unittest.mock import MagicMock, patch

from cloudinary.exceptions import BadRequest
import pytest
from fastapi import status

from backend.dependencies import get_current_user
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
@patch("backend.routers.onboarding.cloudinary.uploader.upload")
async def test_onboard_user_success_with_image(mock_cloudinary, client, session):
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

    mock_cloudinary.return_value = {"secure_url": "https://cloudinary.com"}

    data = {"full_name": "Marvelous Tester"}
    files = {"image": ("profile.png", b"fake_binary_png_stream_content", "image/png")}

    response = await client.post("/api/v1/onboarding/user", data=data, files=files)

    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()
    assert res_data["message"] == "User onboarded successfully"
    assert res_data["user_profile"]["full_name"] == "Marvelous Tester"
    assert res_data["user_profile"]["image"] == "https://cloudinary.com"


@pytest.mark.asyncio
@patch("backend.routers.onboarding.cloudinary.uploader.upload")
async def test_onboard_user_success_without_image(mock_cloudinary, client, session):
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
    res_data = response.json()
    assert res_data["user_profile"]["full_name"] == "No Image User"
    assert res_data["user_profile"]["image"] is None
    mock_cloudinary.assert_not_called()


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
@patch("backend.routers.onboarding.cloudinary.uploader.upload")
async def test_onboard_user_fail_cloudinary_exception(mock_cloudinary, client, session):
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

    mock_cloudinary.side_effect = BadRequest("Connection reset by cloud peer")

    data = {"full_name": "Unfortunate User"}
    files = {"image": ("avatar.jpg", b"jpeg_bytes", "image/jpeg")}

    response = await client.post("/api/v1/onboarding/user", data=data, files=files)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Cloudinary upload failed" in response.json()["detail"]


# ============================================================================
# 1. SUCCESS PATHS
# ============================================================================


@pytest.mark.asyncio
@patch("backend.routers.onboarding.cloudinary.uploader.upload")
async def test_onboard_vendor_success_all_files(mock_cloudinary, client, session):
    parent_user = Users(
        id=MOCK_USER_ID,
        email="vendor_owner@gmail.com",
        password="securepassword123",
        username="onboarding_vendor",
        role="user",
    )
    session.add(parent_user)
    await session.commit()
    await session.refresh(parent_user)

    mock_cloudinary.side_effect = [
        {"secure_url": "https://cloudinary.com"},
        {"secure_url": "https://cloudinary.com"},
    ]

    # 3. Serialize your structured schema values inside the form string field
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

    # Pass multi-file streams correctly mapping field parameter definitions
    files = {
        "image": ("profile.png", b"fake_png_data", "image/png"),
        "business_license": ("license.pdf", b"fake_pdf_data", "application/pdf"),
    }

    response = await client.post("/api/v1/onboarding/vendor", data=data, files=files)

    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()
    assert res_data["message"] == "Vendor onboarded successfully"
    assert res_data["image_url"] == "https://cloudinary.com"
    assert res_data["license_url"] == "https://cloudinary.com"


@pytest.mark.asyncio
@patch("backend.routers.onboarding.cloudinary.uploader.upload")
async def test_onboard_vendor_success_no_optional_image(
    mock_cloudinary, client, session
):
    """Test onboarding passes when the optional profile image payload is missing."""
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

    mock_cloudinary.return_value = {"secure_url": "https://cloudinary.com"}

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

    response = await client.post("/api/v1/onboarding/vendor", data=data, files=files)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["image_url"] is None
    assert response.json()["license_url"] == "https://cloudinary.com"


# ============================================================================
# 2. VALIDATION & FAILURE PATHS
# ============================================================================


@pytest.mark.asyncio
async def test_onboard_vendor_fail_invalid_json_payload(client):
    data = {"vendor_data": "corrupt_non_json_string_value_here"}
    files = {"business_license": ("license.png", b"data", "image/png")}

    response = await client.post("/api/v1/onboarding/vendor", data=data, files=files)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_onboard_vendor_fail_invalid_image_extension(client):
    """Verify endpoint validation filters bad image file extensions."""
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

    response = await client.post("/api/v1/onboarding/vendor", data=data, files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid image file extension"


@pytest.mark.asyncio
async def test_onboard_vendor_fail_license_size_exceeded(client):
    """Verify endpoint drops license uploads breaking the 15MB file ceiling constraint."""
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

    response = await client.post("/api/v1/onboarding/vendor", data=data, files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Business license size is too large" in response.json()["detail"]
