import redis.asyncio as aioredis

from backend.constants.main import SESSION_EXPIRY_TOKEN
from backend.core.config import config as cfg

redis = aioredis.from_url(url=cfg.REDIS_URL, decode_responses=True)


async def add_token_to_blocklist(token: str, expiry: int = SESSION_EXPIRY_TOKEN):
    return await redis.set(name=token, value="", ex=expiry, nx=True)


async def token_in_blocklist(token: str):
    token = await redis.get(name=token)

    return token is not None
