"""Use case for listing rules created by a specific administrator."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.repositories import RuleRepository


def list_rules_by_creator(session: Session, creator_id: int) -> Sequence[Rule]:
    """Return all active rules created by the administrator identified by ``creator_id``."""

    repository = RuleRepository(session)
    return repository.list_by_creator(creator_id)


__all__ = ["list_rules_by_creator"]
