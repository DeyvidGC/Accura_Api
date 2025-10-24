"""Use case for retrieving a template."""

from sqlalchemy.orm import Session

from app.domain.entities import Template
from app.infrastructure.repositories import TemplateRepository


def get_template(session: Session, template_id: int) -> Template:
    """Return the template identified by ``template_id`` or raise an error."""

    repository = TemplateRepository(session)
    template = repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")
    return template
