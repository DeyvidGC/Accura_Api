"""Use case for updating user information."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import UserRepository
from app.infrastructure.security import get_password_hash


def update_user(
    session: Session,
    user_id: int,
    *,
    name: str | None = None,
    alias: str | None = None,
    email: str | None = None,
    password: str | None = None,
    must_change_password: bool | None = None,
    updated_by: int | None = None,
):
    """Update the provided user and return the new representation."""

    repository = UserRepository(session)
    user = repository.get(user_id)
    if not user:
        msg = "Usuario no encontrado"
        raise ValueError(msg)

    if email and email != user.email:
        existing = repository.get_by_email(email)
        if existing and existing.id != user.id:
            msg = "El correo electrónico ya está registrado"
            raise ValueError(msg)
        user.email = email

    if name is not None:
        user.name = name
    if alias is not None:
        user.alias = alias
    if password is not None:
        user.password = get_password_hash(password)
    if must_change_password is not None:
        user.must_change_password = must_change_password

    user.updated_by = updated_by
    return repository.update(user)
