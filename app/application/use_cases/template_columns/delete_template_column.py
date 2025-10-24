"""Use case for deleting template columns."""

from sqlalchemy.orm import Session

from app.infrastructure.dynamic_tables import create_template_table, drop_template_table
from app.infrastructure.repositories import TemplateColumnRepository, TemplateRepository


def delete_template_column(
    session: Session, *, template_id: int, column_id: int
) -> None:
    """Delete a template column and update the physical table if needed."""

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)

    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    column = column_repository.get(column_id)
    if column is None or column.template_id != template_id:
        raise ValueError("Columna no encontrada")

    column_repository.delete(column_id)

    if template.status == "published":
        updated_template = template_repository.get(template_id)
        try:
            drop_template_table(template.table_name)
            create_template_table(updated_template.table_name, updated_template.columns)
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc
