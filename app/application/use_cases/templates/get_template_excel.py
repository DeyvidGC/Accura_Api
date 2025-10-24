"""Use case for retrieving the Excel file associated with a template."""

from pathlib import Path

from sqlalchemy.orm import Session

from app.infrastructure.repositories import TemplateRepository
from app.infrastructure.template_files import template_excel_path


def get_template_excel(session: Session, *, template_id: int) -> Path:
    """Return the filesystem path to the template Excel file."""

    repository = TemplateRepository(session)
    template = repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    path = template_excel_path(template.id, template.name)
    if not path.exists():
        raise ValueError("Archivo de plantilla no encontrado")

    return path


__all__ = ["get_template_excel"]

