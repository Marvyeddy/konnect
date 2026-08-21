import uuid

import pytest

from backend.models.users import Users
from backend.schemas.auth import UserIn
from backend.services.auth import AuthService

auth_service = AuthService()


@pytest.mark.asyncio
async def test_get_user_by_id(session):
    id = uuid.uuid4()
    seeded_data = Users(
        id=id,
        email="testuser@gmail.com",
        password="hashed_password",
        username="testuser",
    )
    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    # Pass UUID directly, not str(id)
    user = await auth_service.get_user_by_id(id, session)

    assert user is not None
    assert user.id == id
    assert user.email == "testuser@gmail.com"
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_get_user_by_email(session):
    seeded_data = Users(
        email="testuser@gmail.com", password="hashed-password", username="testuser"
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    user = await auth_service.get_user_by_email(seeded_data.email, session)

    assert user is not None
    assert user.email == "testuser@gmail.com"


@pytest.mark.asyncio
async def test_create_user(session):
    user_data = UserIn(
        email="testuser@gmail.com", password="non-hashed-password", username="testuser"
    )

    new_user = await auth_service.create_user(user_data, session)

    assert new_user is not None
    assert new_user.email == "testuser@gmail.com"
    assert new_user.password != "non-hashed-password"


@pytest.mark.asyncio
async def test_update_user(session):
    id = uuid.uuid4()
    seeded_data = Users(
        id=id,
        email="testuser@gmail.com",
        password="hashed-password",
        username="testuser",
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    updated_user = await auth_service.update_user(
        id, {"username": "marvelous"}, session
    )

    assert updated_user is not None
    assert updated_user.username == "marvelous"


@pytest.mark.asyncio
async def test_delete_user(session):
    id = uuid.uuid4()
    seeded_data = Users(
        id=id,
        email="testuser@gmail.com",
        password="hashed-password",
        username="testuser",
    )

    session.add(seeded_data)
    await session.commit()
    await session.refresh(seeded_data)

    await auth_service.delete_user(id, session)

    # Verify the user is actually deleted
    result = await auth_service.get_user_by_id(id, session)
    assert result is None


@pytest.mark.asyncio
async def test_user_not_found_cases(session):
    non_existent_id = uuid.uuid4()
    non_existent_email = "nonexistent@example.com"

    assert await auth_service.get_user_by_id(non_existent_id, session) is None
    assert await auth_service.get_user_by_email(non_existent_email, session) is None
    assert (
        await auth_service.update_user(
            non_existent_id, {"username": "shouldfail"}, session
        )
        is None
    )

    # Should return False, not raise
    result = await auth_service.delete_user(non_existent_id, session)
    assert result is False
