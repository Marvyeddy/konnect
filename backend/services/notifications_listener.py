import json

import redis.asyncio as redis

from backend.services.sse_manager import notification_manager
from backend.core.config import config as cfg


async def listen_for_notifications():
    redis_client = redis.from_url(
        cfg.REDIS_URL,
        decode_responses=True,
    )

    pubsub = redis_client.pubsub()

    await pubsub.subscribe("notifications")

    print("Subscribed to notifications")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            event = json.loads(message["data"])

            recipient_ids = event["recipient_ids"]
            data = event["data"]

            await notification_manager.broadcast(
                recipient_ids,
                data,
            )

    finally:
        await pubsub.unsubscribe("notifications")
        await pubsub.aclose()
        await redis_client.aclose()
