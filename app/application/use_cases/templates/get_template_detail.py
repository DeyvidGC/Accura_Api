"""Use case for retrieving the full template details for a user."""

from sqlalchemy.orm import Session

from app.domain.entities import Template, User
from app.infrastructure.repositories import (
    TemplateRepository,
    TemplateUserAccessRepository,
)
from app.utils import now_in_app_timezone


def get_template_detail(
    session: Session,
    *,
    template_id: int,
    requesting_user: User,
) -> Template:
    """Return template details ensuring the ``requesting_user`` can access them."""

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

    return template


__all__ = ["get_template_detail"]

