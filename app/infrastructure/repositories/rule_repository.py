"""Persistence layer for validation rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.domain.entities import Rule
from app.infrastructure.models import RuleModel


class RuleRepository:
    """Provide CRUD operations for validation rules."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        creator_id: int | None = None,
    ) -> Sequence[Rule]:
        query = self.session.query(RuleModel).filter(RuleModel.deleted.is_(False))
        if creator_id is not None:
            query = query.filter(RuleModel.created_by == creator_id)
        query = query.order_by(desc(RuleModel.created_at), desc(RuleModel.id))
        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def list_recent(
        self, *, limit: int = 5, creator_id: int | None = None
    ) -> Sequence[Rule]:
        query = self.session.query(RuleModel).filter(RuleModel.deleted.is_(False))
        if creator_id is not None:
            query = query.filter(RuleModel.created_by == creator_id)
        query = query.order_by(desc(RuleModel.id))
        if limit is not None:
            query = query.limit(limit)
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

    def find_conflicting_rule_name(
        self,
        candidate_names: Sequence[str],
        *,
        created_by: int | None = None,
        exclude_rule_id: int | None = None,
    ) -> str | None:
        normalized_candidates = {
            name.strip().lower()
            for name in candidate_names
            if isinstance(name, str) and name.strip()
        }
        if not normalized_candidates:
            return None

        query = self.session.query(RuleModel.id, RuleModel.rule).filter(
            RuleModel.deleted.is_(False)
        )
        if created_by is None:
            query = query.filter(RuleModel.created_by.is_(None))
        else:
            query = query.filter(RuleModel.created_by == created_by)
        if exclude_rule_id is not None:
            query = query.filter(RuleModel.id != exclude_rule_id)

        for _, rule_data in query.all():
            for existing_name in self._extract_rule_names(rule_data):
                if existing_name.lower() in normalized_candidates:
                    return existing_name
        return None

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

    @staticmethod
    def _extract_rule_names(rule_data) -> list[str]:
        names: list[str] = []
        RuleRepository._collect_rule_names(rule_data, names)

        unique_names: list[str] = []
        seen: set[str] = set()
        for name in names:
            normalized = name.lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_names.append(name)
        return unique_names

    @staticmethod
    def _collect_rule_names(rule_data, names: list[str]) -> None:
        if isinstance(rule_data, Mapping):
            raw_name = rule_data.get("Nombre de la regla")
            if isinstance(raw_name, str):
                stripped = raw_name.strip()
                if stripped:
                    names.append(stripped)
            for value in rule_data.values():
                RuleRepository._collect_rule_names(value, names)
            return

        if isinstance(rule_data, Sequence) and not isinstance(rule_data, (str, bytes)):
            for entry in rule_data:
                RuleRepository._collect_rule_names(entry, names)


__all__ = ["RuleRepository"]
