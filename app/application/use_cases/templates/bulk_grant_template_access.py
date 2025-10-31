"""Use case for granting template access in bulk."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import TemplateUserAccess

from .grant_template_access import grant_template_access


def bulk_grant_template_access(
    session: Session,
    *,
    grants: Sequence[dict],
) -> list[TemplateUserAccess]:
    """Grant access for the provided ``grants`` definitions."""

    accesses: list[TemplateUserAccess] = []
    for grant in grants:
        accesses.append(
            grant_template_access(
                session,
                template_id=grant["template_id"],
                user_id=grant["user_id"],
                start_date=grant.get("start_date"),
                end_date=grant.get("end_date"),
            )
        )
    return accesses


__all__ = ["bulk_grant_template_access"]
