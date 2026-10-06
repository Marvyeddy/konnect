from celery import Celery
from backend.core.config import config as cfg

broker_url = cfg.CELERY_BROKER_URL

if not broker_url:
    raise RuntimeError("CELERY_BROKER_URL is not configured")

celery_app = Celery(
    "konnect",
    broker=broker_url,
    include=["backend.tasks.email_tasks", "backend.tasks.notification_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    autoretry_for=(Exception),
    retry_backoff=True,
    max_retries=5,
)
