"""Use case for updating validation rules."""

from typing import Any

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def update_rule(
    session: Session,
    *,
    rule_id: int,
    name: str | None = None,
    rule: dict[str, Any] | list[Any] | None = None,
) -> Rule:
    """Update a validation rule ensuring name uniqueness."""

    repository = RuleRepository(session)
    current = repository.get(rule_id)
    if current is None:
        raise ValueError("Regla no encontrada")

    new_name = name if name is not None else current.name
    new_rule = rule if rule is not None else current.rule

    if new_name != current.name:
        existing = repository.get_by_name(new_name)
        if existing and existing.id != rule_id:
            msg = "Ya existe una regla con ese nombre"
            raise ValueError(msg)

    entity = Rule(id=rule_id, name=new_name, rule=new_rule)
    return repository.update(entity)
