"""Use case for retrieving the Excel file associated with a template."""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import TemplateRepository, TemplateUserAccessRepository
from app.infrastructure.template_files import template_excel_path


def get_template_excel(
    session: Session,
    *,
    template_id: int,
    requesting_user: User,
) -> Path:
    """Return the filesystem path to the template Excel file."""

    repository = TemplateRepository(session)
    template = repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    if not requesting_user.is_admin():
        access_repository = TemplateUserAccessRepository(session)
        access = access_repository.get_active_access(
            user_id=requesting_user.id,
            template_id=template_id,
            reference_time=datetime.utcnow(),
        )
        if access is None:
            raise ValueError("El usuario no tiene acceso a la plantilla")

    path = template_excel_path(template.id, template.name)
    if not path.exists():
        raise ValueError("Archivo de plantilla no encontrado")

    return path


__all__ = ["get_template_excel"]

