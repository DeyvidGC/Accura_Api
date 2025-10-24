"""Persistence layer for validation rules."""

from collections.abc import Sequence

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.models import RuleModel


class RuleRepository:
    """Provide CRUD operations for validation rules."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, skip: int = 0, limit: int = 100) -> Sequence[Rule]:
        query = self.session.query(RuleModel).offset(skip).limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def list_recent(self, limit: int = 5) -> Sequence[Rule]:
        query = self.session.query(RuleModel).order_by(desc(RuleModel.id)).limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def get(self, rule_id: int) -> Rule | None:
        model = self._get_model(id=rule_id)
        return self._to_entity(model) if model else None

    def get_by_name(self, name: str) -> Rule | None:
        model = self._get_model(name=name)
        return self._to_entity(model) if model else None

    def create(self, rule: Rule) -> Rule:
        model = RuleModel()
        self._apply_entity_to_model(model, rule)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def update(self, rule: Rule) -> Rule:
        model = self._get_model(id=rule.id)
        if not model:
            msg = f"Rule with id {rule.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, rule)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def delete(self, rule_id: int) -> None:
        model = self._get_model(id=rule_id)
        if not model:
            msg = f"Rule with id {rule_id} not found"
            raise ValueError(msg)
        self.session.delete(model)
        self.session.commit()

    @staticmethod
    def _to_entity(model: RuleModel) -> Rule:
        return Rule(id=model.id, name=model.name, rule=model.rule)

    def _get_model(self, **filters) -> RuleModel | None:
        return self.session.query(RuleModel).filter_by(**filters).first()

    @staticmethod
    def _apply_entity_to_model(model: RuleModel, rule: Rule) -> None:
        model.name = rule.name
        model.rule = rule.rule


__all__ = ["RuleRepository"]
