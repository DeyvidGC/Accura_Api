"""Common validation helpers for user use cases."""


GMAIL_DOMAIN = "gmail.com"


def ensure_valid_gmail(email: str) -> str:
    """Return a normalized Gmail address or raise ``ValueError``."""

    normalized = email.strip()
    if normalized.count("@") != 1:
        raise ValueError("El correo electrónico debe ser una cuenta de Gmail válida")

    local_part, domain = normalized.split("@", 1)
    if not local_part:
        raise ValueError("El correo electrónico debe ser una cuenta de Gmail válida")

    if domain.lower() != GMAIL_DOMAIN:
        raise ValueError("El correo electrónico debe ser una cuenta de Gmail válida")

    return f"{local_part.lower()}@{GMAIL_DOMAIN}"
