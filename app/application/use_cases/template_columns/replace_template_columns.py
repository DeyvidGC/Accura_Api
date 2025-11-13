"""Use case for replacing all template columns with new definitions."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import TemplateColumn
from app.infrastructure.repositories import (
    TemplateColumnRepository,
    TemplateRepository,
)

from .create_template_column import (
    NewTemplateColumnData,
    create_template_columns,
)


def replace_template_columns(
    session: Session,
    *,
    template_id: int,
    columns: Sequence[NewTemplateColumnData],
    actor_id: int | None = None,
) -> list[TemplateColumn]:
    """Replace all columns of a template with the provided definitions."""

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)

    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    if template.status == "published":
        raise ValueError("No se pueden modificar las columnas de una plantilla publicada")

    existing_columns = list(column_repository.list_by_template(template_id))
    for column in existing_columns:
        column_repository.delete(column.id, deleted_by=actor_id)

    if not columns:
        return []

    return create_template_columns(
        session,
        template_id=template_id,
        columns=columns,
        created_by=actor_id,
    )


__all__ = [
    "replace_template_columns",
]
