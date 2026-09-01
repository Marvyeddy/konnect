from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import create_url_safe_token
from backend.models.users import Users


# ---------------------------------
# CREATE USER TEST
# ---------------------------------
@pytest.mark.asyncio
@patch("backend.routers.auth.send_email")
async def test_create_new_user_success(mock_send_email, client, session: AsyncSession):
    payload = {
        "email": "testuser@gmail.com",
        "username": "testuser",
        "password": "not-hashed-password",
    }

    response = await client.post("/api/v1/auth/signup", json=payload)

    assert response.status_code == 201

    data = response.json()
    assert data["message"] == "User created successfully"
    assert "session_token" in data
    assert "refresh_token" in data

    assert "session_token" in response.cookies
    assert "refresh_token" in response.cookies
    assert response.cookies["session_token"] == data["session_token"]
    assert response.cookies["refresh_token"] == data["refresh_token"]

    mock_send_email.assert_called_once()


@pytest.mark.asyncio
@patch("backend.routers.auth.send_email")
async def test_current_user_already_exists(
    mock_send_email, client, session: AsyncSession
):
    seeded_data = Users(
        email="testuser@gmail.com", username="testuser", password="hashed-password"
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    payload = {
        "email": "testuser@gmail.com",
        "username": "testuser",
        "password": "non-hashed-password",
    }

    response = await client.post("/api/v1/auth/signup", json=payload)

    assert response.status_code == 409

    mock_send_email.assert_not_called()


# ----------------------------------------
# LOGIN USER TEST
# ----------------------------------------
@pytest.mark.asyncio
@patch("backend.routers.auth.verify_pwd")
async def test_login_user_success(mock_verify, client, session: AsyncSession):
    mock_verify.return_value = True

    seeded_data = Users(
        email="testuser@gmail.com", username="testuser", password="hashed-password"
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    payload = {"email": "testuser@gmail.com", "password": "non-hashed-password"}

    response = await client.post("/api/v1/auth/signin", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "session_token" in data
    assert "refresh_token" in data
    assert "session_token" in response.cookies
    assert "refresh_token" in response.cookies
    assert response.cookies["session_token"] == data["session_token"]
    assert response.cookies["refresh_token"] == data["refresh_token"]


@pytest.mark.asyncio
@patch("backend.routers.auth.verify_pwd")
async def test_login_user_wrong_email(mock_verify, client, session: AsyncSession):
    mock_verify.return_value = True

    seeded_data = Users(
        email="testuser@gmail.com", username="testuser", password="hashed-password"
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    payload = {"email": "testwronguser@gmail.com", "password": "non-hashed-password"}

    response = await client.post("/api/v1/auth/signin", json=payload)

    assert response.status_code == 401


@pytest.mark.asyncio
@patch("backend.routers.auth.verify_pwd")
async def test_login_user_wrong_password(mock_verify, client, session: AsyncSession):
    mock_verify.return_value = False

    seeded_data = Users(
        email="testuser@gmail.com", username="testuser", password="hashed-password"
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    payload = {"email": "testuser@gmail.com", "password": "non-hashed-password"}

    response = await client.post("/api/v1/auth/signin", json=payload)

    assert response.status_code == 401


# --------------------------------------
# FORGET AND RESET PASSWORD
# --------------------------------------
@pytest.mark.asyncio
@patch("backend.routers.auth.send_email")
async def test_forget_password_success(mock_send_email, client, session: AsyncSession):
    seeded_data = Users(
        email="testuser@gmail.com", username="testuser", password="hashed-password"
    )
    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    payload = {"email": "testuser@gmail.com"}

    response = await client.post("/api/v1/auth/forget-password", params=payload)

    assert response.status_code == 200

    data = response.json()
    assert (
        data["message"]
        == "If an account with that email exists, a password reset link has been sent."
    )

    mock_send_email.assert_called_once()


@pytest.mark.asyncio
@patch("backend.routers.auth.hash_pwd")
async def test_reset_password_success(mock_hash_pwd, client, session: AsyncSession):
    mock_hash_pwd.return_value = "new-hashed-mock-string"

    seeded_user = Users(
        email="resetme@gmail.com",
        username="resetuser",
        password="old-hashed-password",
    )
    session.add(seeded_user)
    await session.commit()
    await session.refresh(seeded_user)

    valid_token = create_url_safe_token({"email": "resetme@gmail.com"})

    payload = {
        "new_password": "brand-new-password123",
        "confirm_password": "brand-new-password123",
    }

    response = await client.post(
        f"/api/v1/auth/reset-password/{valid_token}", json=payload
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password reset successfully"

    await session.refresh(seeded_user)
    assert seeded_user.password == "new-hashed-mock-string"
    assert seeded_user.password != "old-hashed-password"


@pytest.mark.asyncio
@patch("backend.routers.auth.hash_pwd")
async def test_reset_password_fails_on_mismatched_confirmation(
    mock_hash_pwd, client, session: AsyncSession
):
    mock_hash_pwd.return_value = True
    seeded_user = Users(
        email="mismatch@gmail.com",
        username="mismatchuser",
        password="somepassword",
    )
    session.add(seeded_user)
    await session.commit()

    valid_token = create_url_safe_token({"email": "mismatch@gmail.com"})

    payload = {"new_password": "passwordABC", "confirm_password": "passwordXYZ"}

    response = await client.post(
        f"/api/v1/auth/reset-password/{valid_token}", json=payload
    )

    assert response.status_code == 400


# ============================================================================
# 1. WEB LOGOUT TEST (COOKIES)
# ============================================================================


@pytest.mark.asyncio
@patch("backend.routers.auth.add_token_to_blocklist", new_callable=AsyncMock)
@patch("backend.routers.auth.decode_token")
async def test_logout_web_success(mock_decode, mock_add_blocklist, client):
    def mock_decode_side_effect(token):
        if token == "web_session_cookie_val":
            return {"type": "session"}
        if token == "web_refresh_cookie_val":
            return {"type": "refresh"}
        return None

    mock_decode.side_effect = mock_decode_side_effect
    mock_add_blocklist.return_value = None

    # Inject cookies directly into the test client
    client.cookies.set("session_token", "web_session_cookie_val")
    client.cookies.set("refresh_token", "web_refresh_cookie_val")

    response = await client.get("/api/v1/auth/logout")

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Logout successfully"}

    # Verify BOTH tokens were sent to the blocklist with their correct respective expirations
    assert mock_add_blocklist.call_count == 2
    mock_add_blocklist.assert_any_call("web_session_cookie_val", ANY)
    mock_add_blocklist.assert_any_call("web_refresh_cookie_val", ANY)

    # Verify browser cookie removal instructions were sent back in the headers
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any("session_token" in cookie for cookie in set_cookie_headers)
    assert any("refresh_token" in cookie for cookie in set_cookie_headers)


# ============================================================================
# 2. MOBILE LOGOUT TEST (HEADERS)
# ============================================================================


@pytest.mark.asyncio
@patch("backend.routers.auth.add_token_to_blocklist", new_callable=AsyncMock)
@patch("backend.routers.auth.decode_token")
async def test_logout_mobile_success(mock_decode, mock_add_blocklist, client):

    def mock_decode_side_effect(token):
        if token == "mobile_bearer_session_val":
            return {"type": "session"}
        if token == "mobile_custom_refresh_val":
            return {"type": "refresh"}
        return None

    mock_decode.side_effect = mock_decode_side_effect
    mock_add_blocklist.return_value = None

    # Set up mobile headers
    headers = {
        "Authorization": "Bearer mobile_bearer_session_val",
        "X-Refresh-Token": "mobile_custom_refresh_val",
    }

    response = await client.get("/api/v1/auth/logout", headers=headers)

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Logout successfully"}

    # Verify BOTH header tokens hit the blocklist
    assert mock_add_blocklist.call_count == 2
    mock_add_blocklist.assert_any_call("mobile_bearer_session_val", ANY)
    mock_add_blocklist.assert_any_call("mobile_custom_refresh_val", ANY)


# ============================================================================
# 3. EDGE CASE: INVALID TOKEN TYPES DROPPED
# ============================================================================


@pytest.mark.asyncio
@patch("backend.routers.auth.add_token_to_blocklist", new_callable=AsyncMock)
@patch("backend.routers.auth.decode_token")
async def test_logout_ignores_invalid_token_types(
    mock_decode, mock_add_blocklist, client
):
    mock_decode.return_value = {"type": "unknown_or_swapped_type"}
    mock_add_blocklist.return_value = None

    headers = {"Authorization": "Bearer weird_token_type"}
    response = await client.get("/api/v1/auth/logout", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    # Ensure add_token_to_blocklist was NEVER called because types were invalid
    mock_add_blocklist.assert_not_called()


# -----------------------------
# GOOGLE OAUTH TESTS
# -----------------------------


# ============================================================================
# 1. TEST FOR INITIALIZATION REDIRECT
# ============================================================================
@pytest.mark.asyncio
@patch("backend.routers.auth.oauth.google.authorize_redirect", new_callable=AsyncMock)
async def test_auth_google_redirect(mock_authorize_redirect, client):
    # Mock Authlib's built-in redirection response wrapper
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_authorize_redirect.return_value = mock_response

    response = await client.get("/api/v1/auth/google")

    assert response.status_code == 200
    mock_authorize_redirect.assert_called_once()


# ============================================================================
# 2. TEST FOR CALLBACK (NEW USER REGISTRATION)
# ============================================================================
@pytest.mark.asyncio
@patch("backend.routers.auth.send_email", new_callable=AsyncMock)
@patch("backend.routers.auth.create_refresh_token")
@patch("backend.routers.auth.create_session_token")
@patch("backend.routers.auth.auth_service.get_user_by_email", new_callable=AsyncMock)
@patch(
    "backend.routers.auth.oauth.google.authorize_access_token", new_callable=AsyncMock
)
async def test_google_callback_new_user(
    mock_authorize_token,
    mock_get_user,
    mock_create_session,
    mock_create_refresh,
    mock_send_email,
    client,
):
    # 1. Simulate Authlib returning mock token profiles
    mock_authorize_token.return_value = {
        "userinfo": {"email": "newgoogleuser@gmail.com", "sub": "google-unique-id-111"}
    }

    # 2. Mock database state (User does NOT exist yet)
    mock_get_user.return_value = None

    # 3. Mock JWT token string output
    mock_create_session.return_value = "mock_session_jwt"
    mock_create_refresh.return_value = "mock_refresh_jwt"

    response = await client.get("/api/v1/auth/google/callback")

    # Assertions for dynamic signups
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == "User created successfully"
    assert "session_token" in response.cookies
    assert "refresh_token" in response.cookies

    # Verify that background tasks registered the welcome email execution safely
    mock_send_email.assert_called_once()


# ============================================================================
# 3. TEST FOR CALLBACK (EXISTING USER LOG IN)
# ============================================================================
@pytest.mark.asyncio
@patch("backend.routers.auth.auth_service.update_user", new_callable=AsyncMock)
@patch("backend.routers.auth.create_refresh_token")
@patch("backend.routers.auth.create_session_token")
@patch("backend.routers.auth.auth_service.get_user_by_email", new_callable=AsyncMock)
@patch(
    "backend.routers.auth.oauth.google.authorize_access_token", new_callable=AsyncMock
)
async def test_google_callback_existing_user(
    mock_authorize_token,
    mock_get_user,
    mock_create_session,
    mock_create_refresh,
    mock_update_user,
    client,
):
    """Test callback signs in an existing user, updates identifiers, and flags a 200 state."""
    mock_authorize_token.return_value = {
        "userinfo": {"email": "existing@gmail.com", "sub": "google-unique-id-222"}
    }

    # Simulate finding an existing record in the table database
    mock_existing_user = MagicMock()
    mock_existing_user.id = "user-uuid-existing-999"
    mock_existing_user.email = "existing@gmail.com"
    mock_existing_user.role = "user"
    mock_get_user.return_value = mock_existing_user

    mock_create_session.return_value = "mock_session_jwt"
    mock_create_refresh.return_value = "mock_refresh_jwt"

    response = await client.get("/api/v1/auth/google/callback")

    # Assertions for returning visitors
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Logged in successfully (Google)"

    # Verify the database updated the Google authentication mappings
    mock_update_user.assert_called_once()
