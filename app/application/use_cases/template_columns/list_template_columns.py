"""Use case for listing template columns."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import TemplateColumn
from app.infrastructure.repositories import TemplateColumnRepository, TemplateRepository


def list_template_columns(session: Session, template_id: int) -> Sequence[TemplateColumn]:
    """Return all columns defined for a template."""

    template_repository = TemplateRepository(session)
    if template_repository.get(template_id) is None:
        raise ValueError("Plantilla no encontrada")

    repository = TemplateColumnRepository(session)
    return repository.list_by_template(template_id)
