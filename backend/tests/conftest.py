from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from backend.core.config import config as cfg
from backend.external.database import get_session
from backend.main import app


@pytest_asyncio.fixture(autouse=True, scope="function")
async def bypass_middleware_rate_limiter():

    async def mock_call(self, request, call_next):
        return await call_next(request)

    with patch("backend.main.SecurityMiddleware.dispatch", mock_call):
        yield


@pytest_asyncio.fixture()
async def async_engine() -> AsyncEngine:
    engine = create_async_engine(
        url=cfg.TEST_DB_URL,
        echo=False,
        pool_pre_ping=True,
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine) -> AsyncSession:
    Session = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def test_db(async_engine):
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    try:
        yield
    finally:
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture()
async def client(session) -> AsyncClient:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://localhost",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def bypass_redis_globally():
    mock_redis = AsyncMock()

    mock_redis.get.return_value = None

    mock_redis.set.return_value = True

    with patch("backend.external.redis.redis", mock_redis):
        yield mock_redis
