"""Use case for assigning template access to a user."""

from datetime import date, datetime, time

from sqlalchemy.orm import Session

from app.application.use_cases.notifications import notify_template_access_granted
from app.domain.entities import TemplateUserAccess
from app.infrastructure.repositories import (
    TemplateRepository,
    TemplateUserAccessRepository,
    UserRepository,
)


def grant_template_access(
    session: Session,
    *,
    template_id: int,
    user_id: int,
    start_date: date | datetime | None = None,
    end_date: date | datetime | None = None,
) -> TemplateUserAccess:
    """Grant access for ``user_id`` to use the template identified by ``template_id``."""

    template = TemplateRepository(session).get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    user = UserRepository(session).get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    access_repository = TemplateUserAccessRepository(session)

    effective_start = _normalize_date(start_date) or _current_utc_day_start()
    normalized_end = _normalize_date(end_date)
    if normalized_end is not None and normalized_end <= effective_start:
        raise ValueError("La fecha de finalización debe ser posterior a la fecha de inicio")

    existing_access = access_repository.get_active_access(
        user_id=user_id,
        template_id=template_id,
        reference_time=effective_start,
    )
    if existing_access is not None:
        raise ValueError("El usuario ya tiene acceso activo a la plantilla")

    access = TemplateUserAccess(
        id=None,
        template_id=template_id,
        user_id=user_id,
        start_date=effective_start,
        end_date=normalized_end,
        revoked_at=None,
        revoked_by=None,
        created_at=None,
        updated_at=None,
    )

    saved_access = access_repository.create(access)
    notify_template_access_granted(
        session, access=saved_access, template=template, user=user
    )
    return saved_access


def _normalize_date(value: date | datetime | None) -> datetime | None:
    """Return a ``datetime`` value normalized to the start of the day."""

    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    return datetime.combine(value, time.min)


def _current_utc_day_start() -> datetime:
    """Return the UTC start-of-day ``datetime`` for the current day."""

    now = datetime.utcnow()
    return datetime.combine(now.date(), time.min)


__all__ = ["grant_template_access"]
