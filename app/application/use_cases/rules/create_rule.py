"""Use case for creating validation rules."""

from typing import Any

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def create_rule(session: Session, *, rule: dict[str, Any] | list[Any]) -> Rule:
    """Create a new validation rule."""

    repository = RuleRepository(session)

    entity = Rule(id=None, rule=rule)
    return repository.create(entity)
