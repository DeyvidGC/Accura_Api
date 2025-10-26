"""Use case for creating users."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import RoleRepository, UserRepository
from app.infrastructure.security import get_password_hash


def create_user(
    session: Session,
    *,
    name: str,
    role_id: int,
    email: str,
    password: str,
    created_by: int | None = None,
) -> User:
    """Create a new user ensuring unique email addresses."""

    repository = UserRepository(session)
    role_repository = RoleRepository(session)

    if repository.get_by_email(email):
        msg = "El correo electrónico ya está registrado"
        raise ValueError(msg)

    role = role_repository.get(role_id)
    if role is None:
        raise ValueError("Rol no encontrado")

    role_alias = role.alias.lower()
    allowed_roles = role_repository.list_aliases()
    if role_alias not in allowed_roles:
        raise ValueError("Rol no permitido")

    hashed_password = get_password_hash(password)
    now = datetime.utcnow()

    must_change_password = role_alias in allowed_roles

    user = User(
        id=None,
        role=role,
        name=name,
        email=email,
        password=hashed_password,
        must_change_password=must_change_password,
        last_login=None,
        created_by=created_by,
        created_at=now,
        updated_by=None,
        updated_at=None,
        is_active=True,
    )

    return repository.create(user)
