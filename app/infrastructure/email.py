"""Utility helpers for sending transactional email notifications."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def _can_send_email() -> bool:
    """Return ``True`` when the SMTP configuration is complete."""

    settings = get_settings()
    return all(
        [
            settings.smtp_host,
            settings.smtp_sender,
            settings.smtp_username,
            settings.smtp_password,
        ]
    )


def send_email(subject: str, body: str, recipient: str) -> bool:
    """Send an email using the configured SMTP server.

    Parameters
    ----------
    subject:
        Subject of the email message.
    body:
        Plain text body to send.
    recipient:
        Email address of the recipient.

    Returns
    -------
    bool
        ``True`` when the message was sent successfully, ``False`` otherwise.
    """

    if not _can_send_email():
        logger.info("SMTP configuration incomplete; skipping email delivery")
        return False

    settings = get_settings()
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
        logger.exception("Error sending email: %s", exc)
        return False
    return True


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

