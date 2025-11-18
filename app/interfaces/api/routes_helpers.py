"""Helper utilities shared across API route handlers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CredentialsNotificationDecision:
    """Describe how to notify a user about credential changes."""

    should_send: bool
    include_password: bool


def compute_credentials_notification(
    *,
    email_changed: bool,
    password_changed: bool,
    is_admin: bool,
    acting_on_self: bool,
) -> CredentialsNotificationDecision:
    """Return the notification strategy for a credentials update."""

    if email_changed:
        return CredentialsNotificationDecision(should_send=True, include_password=True)

    if password_changed and is_admin:
        # Administrators receive a confirmation email when changing their own
        # password, but the password itself should not be included because they
        # already know it. When acting on other accounts (which should only
        # happen through a reset) the password must be included.
        return CredentialsNotificationDecision(
            should_send=True,
            include_password=not acting_on_self,
        )

    return CredentialsNotificationDecision(should_send=False, include_password=False)
