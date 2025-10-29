"""Use case for listing users created by a specific administrator."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import UserRepository


def list_users_by_creator(session: Session, creator_id: int) -> Sequence[User]:
    """Return all users created by the administrator identified by ``creator_id``."""

    repository = UserRepository(session)
    return repository.list_by_creator(creator_id)
