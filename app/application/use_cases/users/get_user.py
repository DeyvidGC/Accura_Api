"""Use case for retrieving a single user."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import UserRepository


def get_user(session: Session, user_id: int):
    """Return the user matching the provided identifier."""

    repository = UserRepository(session)
    return repository.get(user_id)
