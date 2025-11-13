"""Use case for revoking a previously granted template access."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import TemplateUserAccess
from app.infrastructure.repositories import TemplateRepository, TemplateUserAccessRepository


def revoke_template_access(
    session: Session,
    *,
    template_id: int,
    user_id: int,
    revoked_by: int,
) -> TemplateUserAccess:
    """Revoke the specified access assignment."""

    template = TemplateRepository(session).get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    repository = TemplateUserAccessRepository(session)
    access = repository.get_by_template_and_user(
        template_id=template_id,
        user_id=user_id,
    )
    if access is None:
        raise ValueError("Acceso no encontrado")
    if access.revoked_at is not None:
        raise ValueError("El acceso ya está revocado")

    return repository.revoke(
        access_id=access.id,
        revoked_by=revoked_by,
        revoked_at=datetime.utcnow(),
    )


__all__ = ["revoke_template_access"]
