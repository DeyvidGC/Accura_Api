"""Use case for retrieving the most recently created validation rules."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Rule, User
from app.infrastructure.repositories import RuleRepository


def list_recent_rules(
    session: Session,
    *,
    current_user: User,
    limit: int = 5,
    rule_types: Sequence[str] | None = None,
) -> Sequence[Rule]:
    """Return the most recently created validation rules up to ``limit`` entries."""

    repository = RuleRepository(session)
    creator_id = (
        current_user.id if current_user.is_admin() else current_user.created_by
    )
    if creator_id is None:
        return []
    if rule_types:
        return repository.list_recent_by_type(
            limit=limit, creator_id=creator_id, rule_types=rule_types
        )
    return repository.list_recent(limit=limit, creator_id=creator_id)


__all__ = ["list_recent_rules"]
