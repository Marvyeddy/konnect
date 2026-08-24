from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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
