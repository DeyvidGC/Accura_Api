"""Utility helpers for sending transactional email notifications."""

from __future__ import annotations

import json
import logging
import smtplib
from email.message import EmailMessage
from http.client import HTTPSConnection
from typing import Final

try:  # pragma: no cover - optional dependency for SendGrid SDK integration
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except Exception:  # pragma: no cover - the SDK is optional for runtime environments
    SendGridAPIClient = None  # type: ignore[assignment]
    Mail = None  # type: ignore[assignment]



from app.config import get_settings

logger = logging.getLogger(__name__)

_SENDGRID_DEFAULT_HOST: Final[str] = "api.sendgrid.com"
_SENDGRID_MAIL_PATH: Final[str] = "/v3/mail/send"
_SENDGRID_HOST_BY_REGION: Final[dict[str, str]] = {
    "global": _SENDGRID_DEFAULT_HOST,
    "eu": "api.eu.sendgrid.com",
}

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


def _send_with_sendgrid_sdk(subject: str, body: str, recipient: str) -> bool:
    """Send an email using the official SendGrid SDK when available."""

    if not (SendGridAPIClient and Mail):
        return False

    settings = get_settings()

    try:
        client = SendGridAPIClient(settings.sendgrid_api_key)
    except Exception as exc:  # pragma: no cover - SDK raises informative errors
        logger.exception("Unable to initialize SendGrid client: %s", exc)
        return False

    region = (settings.sendgrid_region or "global").lower()
    try:
        client.set_sendgrid_data_residency(region)
    except AttributeError:  # pragma: no cover - older SDKs may not support residency
        logger.debug("Installed SendGrid SDK does not support data residency configuration")
    except Exception as exc:  # pragma: no cover - invalid region values
        logger.error("Invalid SendGrid region '%s': %s", region, exc)
        return False

    message = Mail(
        from_email=settings.smtp_sender,
        to_emails=recipient,
        subject=subject,
        plain_text_content=body,
    )

    try:
        response = client.send(message)
    except Exception as exc:  # pragma: no cover - network failures are environment specific
        logger.exception("Error sending email via SendGrid SDK: %s", exc)
        return False

    if 200 <= getattr(response, "status_code", 0) < 300:
        return True

    response_body = ""
    if hasattr(response, "body"):
        raw_body = getattr(response, "body")
        if isinstance(raw_body, bytes):
            response_body = raw_body.decode("utf-8", errors="ignore")
        else:
            response_body = str(raw_body)

    logger.error(
        "SendGrid API error: %s %s",
        getattr(response, "status_code", "unknown"),
        response_body,
    )
    return False


def _send_with_sendgrid_http(subject: str, body: str, recipient: str) -> bool:
    """Send an email using the SendGrid REST API via direct HTTPS calls."""

    settings = get_settings()

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

    region = (settings.sendgrid_region or "global").lower()
    host = _SENDGRID_HOST_BY_REGION.get(region, _SENDGRID_DEFAULT_HOST)
    if region not in _SENDGRID_HOST_BY_REGION:
        logger.error("Invalid SendGrid region '%s'; defaulting to global endpoint", region)

    connection = HTTPSConnection(host, timeout=settings.smtp_timeout)
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

def _send_with_sendgrid(subject: str, body: str, recipient: str) -> bool:
    """Send an email using SendGrid via the SDK when available, otherwise HTTP."""

    settings = get_settings()
    if not (settings.sendgrid_api_key and settings.smtp_sender):
        logger.info("SendGrid configuration incomplete; skipping email delivery")
        return False

    if _send_with_sendgrid_sdk(subject, body, recipient):
        return True

    if SendGridAPIClient is None or Mail is None:
        logger.debug("SendGrid SDK not fully available; falling back to HTTP transport")

    return _send_with_sendgrid_http(subject, body, recipient)



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

