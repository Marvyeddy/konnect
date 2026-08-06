import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db.database import get_session
from backend.main import app
from backend.utils.config import Config as cfg

async_engine = AsyncEngine(create_engine(url=cfg.TEST_DB_URL, echo=True))


@pytest_asyncio.fixture()
async def session():
    Session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with Session() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def test_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture()
async def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app, client=("127.0.0.1", 50000)) as test_client:
        yield test_client
    app.dependency_overrides.clear()
