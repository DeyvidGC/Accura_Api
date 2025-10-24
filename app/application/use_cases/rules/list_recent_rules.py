"""Use case for retrieving the most recently created validation rules."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def list_recent_rules(session: Session, *, limit: int = 5) -> Sequence[Rule]:
    """Return the most recently created validation rules up to ``limit`` entries."""

    repository = RuleRepository(session)
    return repository.list_recent(limit=limit)


__all__ = ["list_recent_rules"]
