"""Use case for registering the last login of a user."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import UserRepository
from app.utils import now_in_app_timezone


def record_login(session: Session, user_id: int) -> None:
    """Persist the last login timestamp for the given user."""

    repository = UserRepository(session)
    user = repository.get(user_id)
    if not user:
        return

    user.last_login = now_in_app_timezone()
    repository.update(user)
