import json

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

EXCHANGE_NAME = "app.events"


class RabbitMQ:
    def __init__(self, url: str):
        self._url = url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel = None
        self._exchange = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        await self._ensure_channel()

    async def _ensure_channel(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            return

        self._channel = await self._connection.channel()

        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME,
            ExchangeType.TOPIC,
            durable=True,
        )

    async def publish(
        self,
        routing_key: str,
        payload: dict,
    ) -> None:
        await self._ensure_channel()

        await self._exchange.publish(
            Message(
                json.dumps(payload).encode("utf-8"),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=routing_key,
        )

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
