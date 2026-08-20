import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from backend.core.config import config as cfg
from backend.external.database import get_session
from backend.main import app


@pytest_asyncio.fixture()
async def async_engine() -> AsyncEngine:
    engine = create_async_engine(
        url=cfg.TEST_DB_URL,
        echo=True,
        future=True,
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
        # Drop all tables after the test run
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture()
async def client(session):
    app.dependency_overrides[get_session] = lambda: session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
