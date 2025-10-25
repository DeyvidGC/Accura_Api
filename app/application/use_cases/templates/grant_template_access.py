"""Use case for assigning template access to a user."""

from datetime import datetime

from sqlalchemy.orm import Session

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
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> TemplateUserAccess:
    """Grant access for ``user_id`` to use the template identified by ``template_id``."""

    template = TemplateRepository(session).get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    user = UserRepository(session).get(user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")

    access_repository = TemplateUserAccessRepository(session)

    effective_start = start_date or datetime.utcnow()
    if end_date is not None and end_date <= effective_start:
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
        end_date=end_date,
        revoked_at=None,
        revoked_by=None,
        created_at=None,
        updated_at=None,
    )

    return access_repository.create(access)


__all__ = ["grant_template_access"]
