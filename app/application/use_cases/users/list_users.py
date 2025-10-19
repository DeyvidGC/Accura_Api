"""Use case for listing users."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import UserRepository


def list_users(session: Session, skip: int = 0, limit: int = 100) -> Sequence[User]:
    """Return a paginated list of users."""

    repository = UserRepository(session)
    return repository.list(skip=skip, limit=limit)
