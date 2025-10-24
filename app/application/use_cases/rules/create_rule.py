"""Use case for creating validation rules."""

from typing import Any

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def create_rule(session: Session, *, name: str, rule: dict[str, Any] | list[Any]) -> Rule:
    """Create a new validation rule ensuring name uniqueness."""

    repository = RuleRepository(session)

    if repository.get_by_name(name):
        msg = "Ya existe una regla con ese nombre"
        raise ValueError(msg)

    entity = Rule(id=None, name=name, rule=rule)
    return repository.create(entity)
