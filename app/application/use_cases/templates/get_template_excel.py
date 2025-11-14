"""Use case for retrieving the Excel file associated with a template."""

from pathlib import Path

from sqlalchemy.orm import Session

from app.domain.entities import User
from app.infrastructure.repositories import (
    DigitalFileRepository,
    TemplateRepository,
    TemplateUserAccessRepository,
)
from app.infrastructure.template_files import download_template_excel
from app.utils import now_in_app_timezone


def get_template_excel(
    session: Session,
    *,
    template_id: int,
    requesting_user: User,
) -> tuple[Path, str]:
    """Return the filesystem path and download name for the template Excel file."""

    repository = TemplateRepository(session)
    template = repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    if not requesting_user.is_admin():
        access_repository = TemplateUserAccessRepository(session)
        access = access_repository.get_active_access(
            user_id=requesting_user.id,
            template_id=template_id,
            reference_time=now_in_app_timezone(),
        )
        if access is None:
            raise ValueError("El usuario no tiene acceso a la plantilla")

    digital_file_repository = DigitalFileRepository(session)
    digital_file = digital_file_repository.get_by_template_id(template_id)
    if digital_file is None:
        raise ValueError("Archivo de plantilla no encontrado")

    try:
        path = download_template_excel(digital_file.path)
    except FileNotFoundError as exc:
        raise ValueError("Archivo de plantilla no encontrado") from exc

    download_name = digital_file.name or f"{template.name}.xlsx"
    return path, download_name


__all__ = ["get_template_excel"]

