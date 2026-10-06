import asyncio
from backend.celery_app import celery_app
from backend.external.email import send_email


@celery_app.task
def send_welcome_email_task(email: str, context: dict):
    asyncio.run(
        send_email(
            subject="Welcome to Konnect!",
            recipients=[email],
            template_name="welcome.html",
            context=context,
        )
    )
