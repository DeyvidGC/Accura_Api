"""Use case for listing users."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import UserRepository


def list_users(
    session: Session,
    *,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[User]:
    """Return a list of users respecting pagination parameters."""

    repository = UserRepository(session)
    creator_id = current_user.id if current_user.id is not None else None
    return repository.list(skip=skip, limit=limit, creator_id=creator_id)

