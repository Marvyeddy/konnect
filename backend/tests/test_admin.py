import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from backend.internal.admin import super_admin
from backend.main import app

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

    response = await client.patch(
        f"/api/v1/admin/{TARGET_USER_UUID}/create", headers=VALID_AUTH_HEADERS
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

    response = await client.patch(
        f"/api/v1/admin/{TARGET_USER_UUID}/remove", headers=VALID_AUTH_HEADERS
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
    create_response = await client.patch(
        f"/api/v1/admin/{TARGET_USER_UUID}/create", headers=VALID_AUTH_HEADERS
    )
    remove_response = await client.patch(
        f"/api/v1/admin/{TARGET_USER_UUID}/remove", headers=VALID_AUTH_HEADERS
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

    response = await client.patch(
        f"/api/v1/admin/{invalid_id}/create", headers=VALID_AUTH_HEADERS
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid user ID format. Must be a valid UUID."


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_super_admin_auth")
@patch("backend.internal.admin.auth_service.get_user_by_id", new_callable=AsyncMock)
async def test_make_admin_fail_user_not_found(mock_get_user, client):
    mock_get_user.return_value = None

    response = await client.patch(
        f"/api/v1/admin/{TARGET_USER_UUID}/create", headers=VALID_AUTH_HEADERS
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
        response = await client.patch(
            f"/api/v1/admin/{TARGET_USER_UUID}/create", headers=VALID_AUTH_HEADERS
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Database error during promotion." in response.json()["detail"]
