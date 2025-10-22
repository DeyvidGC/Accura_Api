"""Use case for creating users."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import UserRepository
from app.infrastructure.security import get_password_hash


def create_user(
    session: Session,
    *,
    name: str,
    email: str,
    password: str,
    alias: str | None = None,
    created_by: int | None = None,
    must_change_password: bool = False,
) -> User:
    """Create a new user ensuring unique email addresses."""

    repository = UserRepository(session)

    if repository.get_by_email(email):
        msg = "El correo electrónico ya está registrado"
        raise ValueError(msg)

    hashed_password = get_password_hash(password)
    now = datetime.utcnow()
    user = User(
        id=None,
        name=name,
        alias=alias,
        email=email,
        password=hashed_password,
        must_change_password=must_change_password,
        last_login=None,
        created_by=created_by,
        created_at=now,
        updated_by=created_by,
        updated_at=now,
        is_active=True,
    )

    return repository.create(user)
