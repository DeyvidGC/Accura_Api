"""Use case for retrieving a single validation rule."""

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def get_rule(session: Session, rule_id: int) -> Rule:
    """Return the rule identified by ``rule_id`` or raise an error."""

    repository = RuleRepository(session)
    rule = repository.get(rule_id)
    if rule is None:
        raise ValueError("Regla no encontrada")
    return rule
