"""Use case for deleting a user."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import UserRepository


def delete_user(session: Session, user_id: int) -> None:
    """Delete the specified user from the system."""

    repository = UserRepository(session)
    user = repository.get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")
    repository.delete(user_id)

