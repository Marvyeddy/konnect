import uuid
from datetime import datetime

from pydantic import BaseModel

from backend.constants.main import NotificationType


class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: NotificationType | str = "INFO"
    action_url: str


class NotificationCreate(NotificationBase):
    user_id: uuid.UUID


class NotificationResponse(NotificationBase):
    id: uuid.UUID
    is_read: bool
    created_at: datetime
