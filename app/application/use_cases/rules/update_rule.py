"""Use case for updating validation rules."""

from typing import Any

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def update_rule(
    session: Session,
    *,
    rule_id: int,
    rule: dict[str, Any] | list[Any] | None = None,
) -> Rule:
    """Update a validation rule."""

    repository = RuleRepository(session)
    current = repository.get(rule_id)
    if current is None:
        raise ValueError("Regla no encontrada")

    new_rule = rule if rule is not None else current.rule

    entity = Rule(id=rule_id, rule=new_rule)
    return repository.update(entity)
