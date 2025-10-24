"""Use case for retrieving a template column."""

from sqlalchemy.orm import Session

from app.domain.entities import TemplateColumn
from app.infrastructure.repositories import TemplateColumnRepository


def get_template_column(
    session: Session, *, template_id: int, column_id: int
) -> TemplateColumn:
    """Return a template column ensuring it belongs to the template."""

    repository = TemplateColumnRepository(session)
    column = repository.get(column_id)
    if column is None or column.template_id != template_id:
        raise ValueError("Columna no encontrada")
    return column
