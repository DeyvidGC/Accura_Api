"""Use case for deactivating a user."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import UserRepository


def deactivate_user(session: Session, user_id: int, *, updated_by: int | None = None):
    """Deactivate the specified user."""

    repository = UserRepository(session)
    user = repository.get(user_id)
    if not user:
        msg = "Usuario no encontrado"
        raise ValueError(msg)

    user.is_active = False
    user.updated_by = updated_by
    return repository.update(user)
