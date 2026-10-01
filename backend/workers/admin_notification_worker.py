import asyncio
import json

from sqlalchemy import select

from backend.core.config import config as cfg
from backend.core.rabbitmq import RabbitMQ
from backend.external.database import AsyncSessionLocal
from backend.models.notification import Notification
from backend.models.users import Users


async def process_event(
    routing_key: str,
    payload: dict,
    session_factory,
):
    print(f"RECEIVED EVENT: {routing_key}")
    print(f"PAYLOAD: {payload}")

    async with session_factory() as session:
        result = await session.execute(select(Users.id).where(Users.role == "admin"))

        admin_ids = [uid for uid in result.scalars().all()]

        print(f"ADMIN IDS: {admin_ids}")

        if not admin_ids:
            print("NO ADMIN USERS FOUND")
            return

        is_update = payload.get("is_update", False)
        business_name = payload.get("business_name", "")

        title = (
            "Vendor updated onboarding info"
            if is_update
            else "New vendor verification required"
        )

        body = (
            f"Vendor '{business_name}' resubmitted details for review."
            if is_update
            else f"Vendor '{business_name}' requires document review."
        )

        notifications = [
            Notification(
                user_id=admin_id,
                title=title,
                message=body,
                notification_type="VENDOR_ONBOARDING",
                action_url=f"/vendors/{payload['vendor_id']}",
                is_read=False,
            )
            for admin_id in admin_ids
        ]

        session.add_all(notifications)

        await session.commit()

        print(f"CREATED {len(notifications)} NOTIFICATIONS")


async def main():
    rabbit = RabbitMQ(cfg.RABBITMQ_URL)

    await rabbit.connect()

    await rabbit._ensure_channel()

    channel = rabbit._channel

    await channel.set_qos(prefetch_count=5)

    queue = await channel.declare_queue(
        "notifications",
        durable=True,
    )

    await queue.bind(
        rabbit._exchange,
        routing_key="vendor.#",
    )

    await queue.bind(
        rabbit._exchange,
        routing_key="user.onboarded",
    )

    print("Notification worker listening...")

    try:
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(requeue=False):
                    payload = json.loads(message.body.decode("utf-8"))

                    await process_event(
                        message.routing_key,
                        payload,
                        AsyncSessionLocal,
                    )

    finally:
        await rabbit.close()


if __name__ == "__main__":
    asyncio.run(main())
