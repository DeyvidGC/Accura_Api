"""Persistence layer for validation rules."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.models import RuleModel


class RuleRepository:
    """Provide CRUD operations for validation rules."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, skip: int = 0, limit: int = 100) -> Sequence[Rule]:
        query = (
            self.session.query(RuleModel)
            .filter(RuleModel.deleted.is_(False))
            .offset(skip)
            .limit(limit)
        )
        return [self._to_entity(model) for model in query.all()]

    def list_recent(self, limit: int = 5) -> Sequence[Rule]:
        query = (
            self.session.query(RuleModel)
            .filter(RuleModel.deleted.is_(False))
            .order_by(desc(RuleModel.id))
            .limit(limit)
        )
        return [self._to_entity(model) for model in query.all()]

    def list_by_creator(self, creator_id: int) -> Sequence[Rule]:
        query = (
            self.session.query(RuleModel)
            .filter(RuleModel.deleted.is_(False))
            .filter(RuleModel.created_by == creator_id)
            .order_by(desc(RuleModel.created_at))
        )
        return [self._to_entity(model) for model in query.all()]

    def get(self, rule_id: int) -> Rule | None:
        model = self._get_model(id=rule_id)
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

    def delete(self, rule_id: int, *, deleted_by: int | None = None) -> None:
        model = self._get_model(id=rule_id, include_deleted=True)
        if not model:
            msg = f"Rule with id {rule_id} not found"
            raise ValueError(msg)
        if model.deleted:
            return
        now = datetime.utcnow()
        model.deleted = True
        model.deleted_by = deleted_by
        model.deleted_at = now
        model.is_active = False
        model.updated_by = deleted_by
        model.updated_at = now
        self.session.add(model)
        self.session.commit()

    @staticmethod
    def _to_entity(model: RuleModel) -> Rule:
        return Rule(
            id=model.id,
            rule=model.rule,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_by=model.updated_by,
            updated_at=model.updated_at,
            is_active=model.is_active,
            deleted=model.deleted,
            deleted_by=model.deleted_by,
            deleted_at=model.deleted_at,
        )

    def _get_model(self, include_deleted: bool = False, **filters) -> RuleModel | None:
        query = self.session.query(RuleModel)
        if not include_deleted:
            query = query.filter(RuleModel.deleted.is_(False))
        return query.filter_by(**filters).first()

    @staticmethod
    def _apply_entity_to_model(model: RuleModel, rule: Rule) -> None:
        model.rule = rule.rule
        model.created_by = rule.created_by
        if rule.created_at is not None:
            model.created_at = rule.created_at
        model.updated_by = rule.updated_by
        model.updated_at = rule.updated_at
        model.is_active = rule.is_active
        model.deleted = rule.deleted
        model.deleted_by = rule.deleted_by
        model.deleted_at = rule.deleted_at


__all__ = ["RuleRepository"]
