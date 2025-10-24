"""Use case for listing templates."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Template
from app.infrastructure.repositories import TemplateRepository


def list_templates(
    session: Session, *, skip: int = 0, limit: int = 100
) -> Sequence[Template]:
    """Return a paginated list of templates."""

    repository = TemplateRepository(session)
    return repository.list(skip=skip, limit=limit)
