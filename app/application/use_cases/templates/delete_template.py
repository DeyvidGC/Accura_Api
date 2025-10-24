"""Use case for deleting templates."""

from sqlalchemy.orm import Session

from app.infrastructure.dynamic_tables import drop_template_table
from app.infrastructure.repositories import TemplateRepository


def delete_template(session: Session, template_id: int) -> None:
    """Delete the template and its dynamic table if necessary."""

    repository = TemplateRepository(session)
    template = repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    repository.delete(template_id)

    if template.status == "published":
        try:
            drop_template_table(template.table_name)
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc
