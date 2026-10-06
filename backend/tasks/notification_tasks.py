import asyncio
import json

import redis.asyncio as redis
from sqlalchemy import select

from backend.celery_app import celery_app
from backend.models.notification import Notification
from backend.models.users import Users
from backend.core.config import config as cfg


async def _notify_admins_vendor_onboarding(
    vendor_id: str,
    business_name: str,
    session,
    is_update: bool = False,
):
    result = await session.execute(select(Users.id).where(Users.role == "admin"))

    admin_ids = list(result.scalars().all())

    print(f"ADMIN IDS: {admin_ids}")

    if not admin_ids:
        print("NO ADMIN USERS FOUND")
        return

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
            action_url=f"/vendors/{vendor_id}",
            is_read=False,
        )
        for admin_id in admin_ids
    ]

    session.add_all(notifications)

    await session.commit()

    print(f"CREATED {len(notifications)} NOTIFICATIONS")

    # Publish event for the FastAPI SSE process.
    redis_client = redis.from_url(
        cfg.REDIS_URL,
        decode_responses=True,
    )

    try:
        event = {
            "admin_ids": [str(admin_id) for admin_id in admin_ids],
            "data": {
                "title": title,
                "message": body,
                "notification_type": "VENDOR_ONBOARDING",
                "action_url": f"/vendors/{vendor_id}",
                "is_read": False,
            },
        }

        await redis_client.publish(
            "admin_notifications",
            json.dumps(event),
        )

    finally:
        await redis_client.aclose()


@celery_app.task(
    name="notifications.vendor_onboarding",
)
def notify_admins_vendor_onboarding(
    vendor_id: str,
    business_name: str,
    session,
    is_update: bool = False,
):
    asyncio.run(
        _notify_admins_vendor_onboarding(
            vendor_id=vendor_id,
            business_name=business_name,
            session=session,
            is_update=is_update,
        )
    )
