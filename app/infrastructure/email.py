"""Utility helpers for sending transactional email notifications."""

from __future__ import annotations

import json
import logging
import smtplib
from email.message import EmailMessage
from http.client import HTTPSConnection
from typing import Final

from app.config import get_settings

logger = logging.getLogger(__name__)

_SENDGRID_HOST: Final[str] = "api.sendgrid.com"
_SENDGRID_MAIL_PATH: Final[str] = "/v3/mail/send"


def _can_send_email() -> bool:
    """Return ``True`` when either SMTP or SendGrid configuration is complete."""

    settings = get_settings()
    if settings.sendgrid_api_key and settings.smtp_sender:
        return True
    return all(
        [
            settings.smtp_host,
            settings.smtp_sender,
            settings.smtp_username,
            settings.smtp_password,
        ]
    )


def _send_with_smtp(subject: str, body: str, recipient: str) -> bool:
    """Send an email using the configured SMTP server."""

    settings = get_settings()
    if not all(
        [
            settings.smtp_host,
            settings.smtp_sender,
            settings.smtp_username,
            settings.smtp_password,
        ]
    ):
        logger.info("SMTP configuration incomplete; skipping email delivery")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_sender
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout) as server:
            if settings.smtp_starttls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:  # pragma: no cover - network failures are environment specific
        logger.exception("Error sending email via SMTP: %s", exc)
        return False
    return True


def _send_with_sendgrid(subject: str, body: str, recipient: str) -> bool:
    """Send an email using the SendGrid REST API."""

    settings = get_settings()
    if not (settings.sendgrid_api_key and settings.smtp_sender):
        logger.info("SendGrid configuration incomplete; skipping email delivery")
        return False

    payload = {
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": settings.smtp_sender},
        "subject": subject,
        "content": [
            {
                "type": "text/plain",
                "value": body,
            }
        ],
    }

    connection = HTTPSConnection(_SENDGRID_HOST, timeout=settings.smtp_timeout)
    try:
        connection.request(
            "POST",
            _SENDGRID_MAIL_PATH,
            body=json.dumps(payload),
            headers={
                "Authorization": f"Bearer {settings.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        # SendGrid returns HTTP 202 for accepted messages
        if 200 <= response.status < 300:
            return True
        logger.error(
            "SendGrid API error: %s %s",
            response.status,
            response.read().decode("utf-8", errors="ignore"),
        )
        return False
    except Exception as exc:  # pragma: no cover - network failures are environment specific
        logger.exception("Error sending email via SendGrid: %s", exc)
        return False
    finally:
        try:
            connection.close()
        except Exception:  # pragma: no cover - best-effort cleanup
            pass


def send_email(subject: str, body: str, recipient: str) -> bool:
    """Send an email using SendGrid when configured, otherwise fallback to SMTP."""

    if not _can_send_email():
        logger.info("Email configuration incomplete; skipping email delivery")
        return False

    settings = get_settings()
    if settings.sendgrid_api_key:
        return _send_with_sendgrid(subject, body, recipient)
    return _send_with_smtp(subject, body, recipient)


def send_new_user_credentials_email(email: str, password: str) -> bool:
    """Send a welcome email containing the credentials for the new user."""

    subject = "Bienvenido a Accura"
    body = (
        "Hola,\n\n"
        "Tu usuario ha sido creado correctamente.\n"
        f"Correo: {email}\n"
        f"Contraseña: {password}\n\n"
        "Por favor, inicia sesión y actualiza tu contraseña lo antes posible.\n"
    )
    return send_email(subject, body, email)

