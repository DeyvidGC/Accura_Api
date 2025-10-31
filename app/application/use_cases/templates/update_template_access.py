"""Use case for updating template access assignments."""

from datetime import date, datetime, time

from sqlalchemy.orm import Session

from app.domain.entities import TemplateUserAccess
from app.infrastructure.repositories import TemplateRepository, TemplateUserAccessRepository


def update_template_access(
    session: Session,
    *,
    template_id: int,
    access_id: int,
    start_date: date | datetime | None = None,
    end_date: date | datetime | None = None,
) -> TemplateUserAccess:
    """Update the configured access window for ``access_id``."""

    template = TemplateRepository(session).get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    repository = TemplateUserAccessRepository(session)
    access = repository.get(access_id)
    if access is None or access.template_id != template_id:
        raise ValueError("Acceso no encontrado")
    if access.revoked_at is not None:
        raise ValueError("No se puede actualizar un acceso revocado")

    normalized_start = _normalize_date(start_date) if start_date is not None else access.start_date
    normalized_end = _normalize_date(end_date) if end_date is not None else access.end_date

    if normalized_end is not None and normalized_end <= normalized_start:
        raise ValueError("La fecha de finalización debe ser posterior a la fecha de inicio")

    updated_access = TemplateUserAccess(
        id=access.id,
        template_id=access.template_id,
        user_id=access.user_id,
        start_date=normalized_start,
        end_date=normalized_end,
        revoked_at=access.revoked_at,
        revoked_by=access.revoked_by,
        created_at=access.created_at,
        updated_at=datetime.utcnow(),
    )

    return repository.update(updated_access)


def _normalize_date(value: date | datetime | None) -> datetime | None:
    """Return a ``datetime`` value normalized to the start of the day."""

    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    return datetime.combine(value, time.min)


__all__ = ["update_template_access"]
