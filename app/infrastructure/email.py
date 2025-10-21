"""Utility helpers for sending transactional email notifications via SendGrid."""

from __future__ import annotations

import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_email(subject: str, html_content: str, recipient: str) -> bool:
    """Send an email using the configured SendGrid credentials."""

    settings = get_settings()
    if not (settings.sendgrid_api_key and settings.sendgrid_sender):
        logger.info("SendGrid configuration incomplete; skipping email delivery")
        return False

    message = Mail(
        from_email=settings.sendgrid_sender,
        to_emails=recipient,
        subject=subject,
        html_content=html_content,
    )

    try:
        client = SendGridAPIClient(settings.sendgrid_api_key)
        response = client.send(message)
    except Exception as exc:  # pragma: no cover - network failures depend on environment
        logger.exception("Error sending email via SendGrid: %s", exc)
        return False

    return 200 <= getattr(response, "status_code", 0) < 300


def send_new_user_credentials_email(email: str, password: str) -> bool:
    """Send a welcome email containing the credentials for the new user."""

    subject = "Bienvenido a Accura"
    html_content = (
        "<p>Hola,</p>"
        "<p>Tu usuario ha sido creado correctamente.</p>"
        f"<p><strong>Correo:</strong> {email}<br><strong>Contraseña:</strong> {password}</p>"
        "<p>Por favor, inicia sesión y actualiza tu contraseña lo antes posible.</p>"
    )
    return send_email(subject, html_content, email)

