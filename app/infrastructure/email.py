"""Simple SMTP email sender."""

import smtplib
from email.message import EmailMessage

from app.config import get_settings

settings = get_settings()


def send_user_created_email(to_email: str, name: str) -> None:
    """Send an email notifying the user that their account was created."""

    if not settings.smtp_host or not settings.smtp_sender:
        # If SMTP configuration is missing we simply skip sending the email.
        return

    message = EmailMessage()
    message["From"] = settings.smtp_sender
    message["To"] = to_email
    message["Subject"] = "Tu cuenta ha sido creada"
    message.set_content(
        (
            "Hola {name},\n\n"
            "Tu cuenta en la plataforma se ha creado correctamente. "
            "Ya puedes iniciar sesión utilizando tus credenciales.\n\n"
            "Saludos."
        ).format(name=name)
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
