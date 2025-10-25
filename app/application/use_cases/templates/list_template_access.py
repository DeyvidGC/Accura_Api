"""Use case for listing access assignments for a template."""

from sqlalchemy.orm import Session

from app.domain.entities import TemplateUserAccess
from app.infrastructure.repositories import TemplateRepository, TemplateUserAccessRepository


def list_template_access(
    session: Session,
    *,
    template_id: int,
    include_inactive: bool = False,
) -> list[TemplateUserAccess]:
    """Return access assignments for the given template."""

    template = TemplateRepository(session).get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    repository = TemplateUserAccessRepository(session)
    return list(
        repository.list_by_template(
            template_id=template_id, include_inactive=include_inactive
        )
    )


__all__ = ["list_template_access"]
