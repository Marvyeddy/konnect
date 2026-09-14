from tkinter import Y
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from backend.internal.admin import admin, super_admin
from backend.main import app
from backend.models.users import Users

TARGET_USER_UUID = uuid.uuid4()

VALID_AUTH_HEADERS = {"Authorization": "Bearer mock_valid_super_admin_token"}

# ============================================================================
# HELPER AUTH FIXTURES
# ============================================================================


@pytest.fixture
def mock_super_admin_auth():
    app.dependency_overrides[super_admin] = lambda: True
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_unauthorized_auth():
    def raise_forbidden():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )

    app.dependency_overrides[super_admin] = raise_forbidden
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_admin_auth():
    app.dependency_overrides[admin] = lambda: True
    yield
    app.dependency_overrides.clear()


# ============================================================================
# 1. SUCCESS PATH TESTS (AUTHORIZED)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_super_admin_auth")
@patch("backend.internal.admin.auth_service.update_user", new_callable=AsyncMock)
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
async def test_make_admin_success(mock_get_user, mock_update_user, client):
    mock_profile = MagicMock()
    mock_profile.permission_level = "user"

    mock_user = MagicMock()
    mock_user.user_profile = mock_profile
    mock_get_user.return_value = mock_user
    mock_update_user.return_value = mock_user

    response = await client.get(
        f"/api/v1/admin/create/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"User {TARGET_USER_UUID} is now an admin."}
    assert mock_profile.permission_level == "manager"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_super_admin_auth")
@patch("backend.internal.admin.auth_service.update_user", new_callable=AsyncMock)
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
async def test_remove_admin_success(mock_get_user, mock_update_user, client):
    """Test super_admin can successfully strip admin privileges from a user."""
    mock_profile = MagicMock()
    mock_profile.permission_level = "manager"

    mock_user = MagicMock()
    mock_user.user_profile = mock_profile
    mock_get_user.return_value = mock_user
    mock_update_user.return_value = mock_user

    response = await client.get(
        f"/api/v1/admin/remove/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": f"User {TARGET_USER_UUID} has been stripped of admin privileges."
    }
    assert mock_profile.permission_level is None


# ============================================================================
# 2. SECURITY PATH TESTS (UNAUTHORIZED)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_unauthorized_auth")
async def test_admin_endpoints_raise_403_forbidden_when_unauthorized(client):
    create_response = await client.get(
        f"/api/v1/admin/create/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )
    remove_response = await client.get(
        f"/api/v1/admin/remove/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )

    assert create_response.status_code == status.HTTP_403_FORBIDDEN
    assert remove_response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# 3. VALIDATION & ERROR PATH TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_super_admin_auth")
async def test_admin_endpoints_fail_invalid_uuid_format(client):
    invalid_id = "non-existent-malformed-string-id"

    response = await client.get(
        f"/api/v1/admin/create/{invalid_id}", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid user ID format. Must be a valid UUID."


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_super_admin_auth")
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
async def test_make_admin_fail_user_not_found(mock_get_user, client):
    mock_get_user.return_value = None

    response = await client.get(
        f"/api/v1/admin/create/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"User {TARGET_USER_UUID} not found."


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_super_admin_auth")
@patch("backend.internal.admin.auth_service.update_user", new_callable=AsyncMock)
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
async def test_make_admin_fail_database_rollback(
    mock_get_user, mock_update_user, client
):
    mock_user = MagicMock()
    mock_user.user_profile = None
    mock_get_user.return_value = mock_user
    mock_update_user.return_value = mock_user

    with patch(
        "sqlalchemy.ext.asyncio.AsyncSession.commit",
        side_effect=Exception("Database error"),
    ):
        response = await client.get(
            f"/api/v1/admin/create/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Database error during promotion." in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_admin_auth")
@patch("backend.internal.admin.auth_service.update_user", new_callable=AsyncMock)
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
@patch("backend.internal.admin.send_email", new_callable=AsyncMock)
async def test_verify_vendor_success(
    mock_send_email, mock_get_user, mock_update_user, client
):
    mock_profile = MagicMock()
    mock_profile.verified = False

    mock_user = MagicMock()
    mock_user.role = "pending"
    mock_user.vendor_profile = mock_profile
    mock_get_user.return_value = mock_user
    mock_update_user.return_value = mock_user

    response = await client.get(
        f"/api/v1/admin/verify/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": f"User {TARGET_USER_UUID} has been verified as a vendor."
    }

    assert mock_user.role == "vendor"
    assert mock_profile.verified is True
    mock_send_email.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_admin_auth")
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
async def test_verify_vendor_role_not_pending(mock_get_user, client):
    mock_user = MagicMock()
    mock_user.role = "user"
    mock_get_user.return_value = mock_user

    response = await client.get(
        f"/api/v1/admin/verify/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "User is not pending verification."


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_admin_auth")
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
async def test_user_inactive(mock_get_user, client):
    mock_user = MagicMock()
    mock_user.is_active = True
    mock_get_user.return_value = mock_user

    response = await client.get(
        f"/api/v1/admin/inactive/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": f"User {TARGET_USER_UUID} has been set to inactive."
    }

    assert not mock_user.is_active


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_admin_auth")
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
async def test_user_active(mock_get_user, client):
    mock_user = MagicMock()
    mock_user.is_active = False
    mock_get_user.return_value = mock_user

    response = await client.get(
        f"/api/v1/admin/active/{TARGET_USER_UUID}", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": f"User {TARGET_USER_UUID} has been set to active."
    }

    assert mock_user.is_active


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_admin_auth")
@patch("backend.internal.admin.auth_service.get_user_by_role", new_callable=AsyncMock)
async def test_get_all_users_by_role_success(mock_get_user_by_role, client):
    mock_user_1 = MagicMock()
    mock_user_1.username = "vendor1"
    mock_user_1.role = "vendor"

    mock_user_2 = MagicMock()
    mock_user_2.username = "vendor2"
    mock_user_2.role = "vendor"

    mock_get_user_by_role.return_value = [mock_user_1, mock_user_2]

    response = await client.get(
        "/api/v1/admin/client", params={"role": "vendor"}, headers=VALID_AUTH_HEADERS
    )

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2
    mock_get_user_by_role.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_admin_auth")
@patch("backend.internal.admin.auth_service.get_user_by_role", new_callable=AsyncMock)
async def test_get_all_users_by_role_not_found(mock_get_user_by_role, client):
    # Mock an empty list returned when no users match the role
    mock_get_user_by_role.return_value = []

    response = await client.get(
        "/api/v1/admin/client",
        params={"role": "nonexistent_role"},
        headers=VALID_AUTH_HEADERS,
    )

    # Assertions
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "No users found with role: nonexistent_role"
    mock_get_user_by_role.assert_called_once()
