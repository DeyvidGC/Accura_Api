"""Use case for listing published templates accessible to a user."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Template, User
from app.infrastructure.repositories import TemplateRepository, UserRepository


def list_user_templates(
    session: Session,
    *,
    user_id: int,
    current_user: User,
) -> Sequence[Template]:
    """Return published templates that ``user_id`` can access."""

    if not current_user.is_admin() and current_user.id != user_id:
        raise ValueError("No autorizado")

    user = UserRepository(session).get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    repository = TemplateRepository(session)
    return repository.list(user_id=user_id, statuses=("published",))


__all__ = ["list_user_templates"]
