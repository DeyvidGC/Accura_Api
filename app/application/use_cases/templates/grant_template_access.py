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

    if template.status != "published":
        raise ValueError(
            "No se puede conceder acceso porque la plantilla no está publicada"
        )

    user = UserRepository(session).get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    access_repository = TemplateUserAccessRepository(session)

    effective_start = _normalize_date(start_date) or _current_utc_day_start()
    normalized_end = _normalize_date(end_date, use_end_of_day=True)
    _validate_access_window(effective_start, normalized_end)

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


def _normalize_date(
    value: date | datetime | None, *, use_end_of_day: bool = False
) -> datetime | None:
    """Return a ``datetime`` value normalized to the start or end of the day."""

    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    boundary = time.max if use_end_of_day else time.min
    return datetime.combine(value, boundary)


def _validate_access_window(start: datetime, end: datetime | None) -> None:
    """Validate that the configured access window is chronological."""

    if end is not None and end < start:
        raise ValueError(
            "El rango de fechas no es válido: la fecha de fin debe ser"
            " posterior o igual a la fecha de inicio"
        )


def _current_utc_day_start() -> datetime:
    """Return the UTC start-of-day ``datetime`` for the current day."""

    now = datetime.utcnow()
    return datetime.combine(now.date(), time.min)


__all__ = ["grant_template_access"]
