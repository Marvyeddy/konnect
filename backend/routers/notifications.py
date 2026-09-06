import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_user
from backend.external.database import get_session
from backend.models.notification import Notification
from backend.models.users import Users
from backend.services.sse_manager import notification_manager

notification_router = APIRouter()


@notification_router.get("/stream")
async def stream_notifications(
    current_user: Annotated[Users, Depends(get_current_user)],
):
    async def event_generator():
        queue = await notification_manager.connect(str(current_user.id))
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            notification_manager.disconnect(str(current_user.id), queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@notification_router.patch("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: Annotated[Users, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    query = await session.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = query.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this notification.",
        )

    notification.is_read = True
    await session.commit()

    return {"success": True, "message": "Notification marked as read."}
