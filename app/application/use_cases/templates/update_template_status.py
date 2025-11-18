"""Use case for updating only the status of a template."""

from sqlalchemy.orm import Session

from app.domain.entities import Template

from .update_template import update_template


def update_template_status(
    session: Session,
    *,
    template_id: int,
    status: str,
    updated_by: int | None = None,
) -> Template:
    """Update only the status of a template."""

    return update_template(
        session,
        template_id=template_id,
        status=status,
        updated_by=updated_by,
    )


__all__ = ["update_template_status"]

