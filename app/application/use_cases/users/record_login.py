"""Use case for registering the last login of a user."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.infrastructure.repositories import UserRepository


def record_login(session: Session, user_id: int) -> None:
    """Persist the last login timestamp for the given user."""

    repository = UserRepository(session)
    user = repository.get(user_id)
    if not user:
        return

    user.last_login = datetime.utcnow()
    repository.update(user)
