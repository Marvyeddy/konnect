from pathlib import Path
from typing import Any

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.utils.config import Config as cfg
from backend.utils.logging import get_app_logger

logger = get_app_logger(__name__)

EMAIL_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"

template_env = Environment(
    loader=FileSystemLoader(EMAIL_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml", "py"]),
)

mail = ConnectionConfig(
    MAIL_USERNAME=cfg.MAIL_USERNAME,
    MAIL_PASSWORD=cfg.MAIL_PASSWORD,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    MAIL_FROM=cfg.MAIL_FROM,
    MAIL_FROM_NAME=cfg.MAIL_FROM_NAME,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


def render_email_template(template_name: str, context: dict[str, Any]) -> str:
    template = template_env.get_template(template_name)
    return template.render(**context)


async def send_email(
    subject: str,
    recipients: list[str],
    template_name: str,
    template_context: dict[str, Any] | None = None,
) -> None:
    body = render_email_template(template_name, template_context or {})

    message = MessageSchema(
        subject=subject, recipients=recipients, body=body, subtype=MessageType.html
    )

    fm = FastMail(mail)
    email = await fm.send_message(message)
    logger.info("Email successfully sent to %s", recipients[0])
    return email
