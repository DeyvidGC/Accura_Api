"""Use case for deleting validation rules."""

from sqlalchemy.orm import Session

from app.infrastructure.repositories import RuleRepository


def delete_rule(session: Session, rule_id: int) -> None:
    """Delete the specified validation rule."""

    repository = RuleRepository(session)
    rule = repository.get(rule_id)
    if rule is None:
        raise ValueError("Regla no encontrada")

    repository.delete(rule_id)
