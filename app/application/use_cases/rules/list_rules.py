"""Use case for listing validation rules."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Rule, User
from app.infrastructure.repositories import RuleRepository


def list_rules(
    session: Session,
    *,
    current_user: User,
    skip: int = 0,
    limit: int | None = 100,
) -> Sequence[Rule]:
    """Return a paginated list of validation rules."""

    repository = RuleRepository(session)
    creator_id = current_user.id if current_user.is_admin() else current_user.created_by
    if creator_id is None:
        return []
    return repository.list(skip=skip, limit=limit, creator_id=creator_id)
