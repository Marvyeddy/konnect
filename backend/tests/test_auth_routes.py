from unittest.mock import patch

import pytest
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
