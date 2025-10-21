"""Use case for updating user information."""

from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import UserRepository
from app.infrastructure.security import get_password_hash


def update_user(
    session: Session,
    *,
    user_id: int,
    name: str,
    email: str,
    alias: str | None = None,
    must_change_password: bool = False,
    is_active: bool = True,
    password: str | None = None,
    updated_by: int | None = None,
) -> User:
    """Update the provided user with the new values."""

    repository = UserRepository(session)
    current_user = repository.get(user_id)
    if current_user is None:
        raise ValueError("Usuario no encontrado")

    existing_with_email = repository.get_by_email(email)
    if existing_with_email and existing_with_email.id != user_id:
        raise ValueError("El correo electrónico ya está registrado")

    updated_user = replace(
        current_user,
        name=name,
        email=email,
        alias=alias,
        must_change_password=must_change_password,
        is_active=is_active,
        updated_by=updated_by,
        updated_at=datetime.utcnow(),
    )

    if password:
        hashed_password = get_password_hash(password)
        updated_user = replace(updated_user, password=hashed_password)

    return repository.update(updated_user)

