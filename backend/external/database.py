from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.orm import sessionmaker
from elasticsearch import AsyncElasticsearch

from backend.core.config import config as cfg

async_engine = create_async_engine(url=cfg.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


es_client = AsyncElasticsearch(cfg.ELASTICSEARCH_URL)
