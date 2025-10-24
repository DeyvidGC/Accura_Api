"""Use case for listing validation rules."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def list_rules(session: Session, *, skip: int = 0, limit: int = 100) -> Sequence[Rule]:
    """Return a paginated list of validation rules."""

    repository = RuleRepository(session)
    return repository.list(skip=skip, limit=limit)
