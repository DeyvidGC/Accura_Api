"""Use case for listing template accesses assigned to a user."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import TemplateUserAccess, User
from app.infrastructure.repositories import (
    TemplateUserAccessRepository,
    UserRepository,
)


def list_user_template_access(
    session: Session,
    *,
    user_id: int,
    current_user: User,
) -> Sequence[TemplateUserAccess]:
    """Return access assignments that belong to ``user_id``."""

    if not current_user.is_admin() and current_user.id != user_id:
        raise ValueError("No autorizado")

    user = UserRepository(session).get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    repository = TemplateUserAccessRepository(session)
    include_inactive = current_user.is_admin()
    include_scheduled = current_user.is_admin()
    return repository.list_by_user(
        user_id=user_id,
        include_inactive=include_inactive,
        include_scheduled=include_scheduled,
    )


__all__ = ["list_user_template_access"]
