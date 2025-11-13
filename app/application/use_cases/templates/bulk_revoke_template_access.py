"""Use case for revoking template access in bulk."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import TemplateUserAccess

from .revoke_template_access import revoke_template_access


def bulk_revoke_template_access(
    session: Session,
    *,
    revocations: Sequence[dict],
    revoked_by: int,
) -> list[TemplateUserAccess]:
    """Revoke template access for the provided ``revocations`` definitions."""

    accesses: list[TemplateUserAccess] = []
    for revocation in revocations:
        accesses.append(
            revoke_template_access(
                session,
                template_id=revocation["template_id"],
                user_id=revocation["user_id"],
                revoked_by=revoked_by,
            )
        )
    return accesses


__all__ = ["bulk_revoke_template_access"]
