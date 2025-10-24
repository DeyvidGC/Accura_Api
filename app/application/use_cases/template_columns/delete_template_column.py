"""Use case for deleting template columns."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import TemplateColumnRepository, TemplateRepository


def delete_template_column(
    session: Session, *, template_id: int, column_id: int
) -> None:
    """Delete a template column.

    Raises:
        ValueError: If the template does not exist, is published or the column is missing.
    """

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)

    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    if template.status == "published":
        raise ValueError("No se pueden modificar las columnas de una plantilla publicada")

    column = column_repository.get(column_id)
    if column is None or column.template_id != template_id:
        raise ValueError("Columna no encontrada")

    column_repository.delete(column_id)
