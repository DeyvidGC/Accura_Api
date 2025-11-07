"""Use case for listing templates."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Template, User
from app.infrastructure.repositories import TemplateRepository


def list_templates(
    session: Session,
    *,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[Template]:
    """Return a paginated list of templates."""

    repository = TemplateRepository(session)
    if current_user.is_admin():
        return repository.list(
            skip=skip, limit=limit, creator_id=current_user.id
        )
    return repository.list(skip=skip, limit=limit, user_id=current_user.id)
