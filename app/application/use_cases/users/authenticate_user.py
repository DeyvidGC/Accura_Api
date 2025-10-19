"""Use case for authenticating a user."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import UserRepository
from app.infrastructure.security import verify_password


def authenticate_user(session: Session, email: str, password: str):
    """Return the user when provided credentials are valid."""

    repository = UserRepository(session)
    user = repository.get_by_email(email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password):
        return None
    return user
