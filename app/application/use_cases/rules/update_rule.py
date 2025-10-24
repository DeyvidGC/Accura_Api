"""Use case for updating validation rules."""

from dataclasses import replace
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def update_rule(
    session: Session,
    *,
    rule_id: int,
    rule: dict[str, Any] | list[Any] | None = None,
    is_active: bool | None = None,
    updated_by: int | None = None,
) -> Rule:
    """Update a validation rule."""

    repository = RuleRepository(session)
    current = repository.get(rule_id)
    if current is None:
        raise ValueError("Regla no encontrada")

    new_rule = rule if rule is not None else current.rule

    updated_rule = replace(
        current,
        rule=new_rule,
        is_active=is_active if is_active is not None else current.is_active,
        updated_by=updated_by if updated_by is not None else current.updated_by,
        updated_at=datetime.utcnow(),
    )

    return repository.update(updated_rule)
