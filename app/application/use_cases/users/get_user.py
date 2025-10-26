"""Use case for retrieving a single user."""

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import UserRepository


def get_user(session: Session, user_id: int, *, include_inactive: bool = False) -> User:
    """Return the requested user or raise an error if it does not exist."""

    repository = UserRepository(session)
    user = repository.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")
    if not include_inactive and not user.is_active:
        raise ValueError("Usuario inactivo")
    return user

