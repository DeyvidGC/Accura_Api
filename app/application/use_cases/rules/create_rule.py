"""Use case for creating validation rules."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def create_rule(
    session: Session,
    *,
    rule: dict[str, Any] | list[Any],
    created_by: int | None = None,
    is_active: bool = True,
) -> Rule:
    """Create a new validation rule."""

    repository = RuleRepository(session)

    now = datetime.utcnow()
    entity = Rule(
        id=None,
        rule=rule,
        created_by=created_by,
        created_at=now,
        updated_by=None,
        updated_at=None,
        is_active=is_active,
    )
    return repository.create(entity)
