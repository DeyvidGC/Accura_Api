"""Use case for updating template access assignments in bulk."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import TemplateUserAccess

from .update_template_access import update_template_access


def bulk_update_template_access(
    session: Session,
    *,
    updates: Sequence[dict],
) -> list[TemplateUserAccess]:
    """Apply the provided ``updates`` to existing access records."""

    accesses: list[TemplateUserAccess] = []
    for update in updates:
        accesses.append(
            update_template_access(
                session,
                template_id=update["template_id"],
                access_id=update["access_id"],
                start_date=update.get("start_date"),
                end_date=update.get("end_date"),
            )
        )
    return accesses


__all__ = ["bulk_update_template_access"]
