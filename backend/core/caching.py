import json
from typing import Any
import redis.asyncio as aioredis
from backend.core.config import config as cfg
from backend.core.logging import get_app_logger


class RedisCache:
    def __init__(self):
        self.r = aioredis.from_url(url=cfg.REDIS_URL, decode_responses=True)
        self.logger = get_app_logger(__name__)

    async def set(self, key: str, value: Any, expiry: int = 3600):
        try:
            json_value = json.dumps(value)
            await self.r.set(key, json_value, ex=expiry)
            self.logger.info(f"Set cache for key: {key} with expiry: {expiry}")
        except aioredis.RedisError as e:
            self.logger.error(f"Redis set error for key {key}: {str(e)}")

    async def get(self, key: str):
        try:
            json_value = await self.r.get(key)
            if json_value is not None:
                self.logger.info(f"Cache hit for key: {key}")
                return json.loads(json_value)
            else:
                self.logger.info(f"Cache miss for key: {key}")
                return None
        except aioredis.RedisError as e:
            self.logger.error(f"Redis get error for key {key}: {str(e)}")
            return None


cache = RedisCache()
