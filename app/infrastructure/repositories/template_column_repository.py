"""Persistence layer for template columns."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.domain.entities import TemplateColumn
from app.infrastructure.models import (
    RuleModel,
    TemplateColumnModel,
    TemplateModel,
    template_column_rule_table,
)


class TemplateColumnRepository:
    """Provide CRUD operations for template columns."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_template(self, template_id: int) -> Sequence[TemplateColumn]:
        query = (
            self.session.query(TemplateColumnModel)
            .options(joinedload(TemplateColumnModel.rules))
            .filter(TemplateColumnModel.template_id == template_id)
            .filter(TemplateColumnModel.deleted.is_(False))
        )
        return [self._to_entity(model) for model in query.all()]

    def get(self, column_id: int) -> TemplateColumn | None:
        model = self._get_model(id=column_id)
        return self._to_entity(model) if model else None

    def create(self, column: TemplateColumn) -> TemplateColumn:
        model = TemplateColumnModel()
        self._apply_entity_to_model(model, column, include_creation_fields=True)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        if model.rules:
            self.session.refresh(model, attribute_names=["rules"])
        return self._to_entity(model)

    def create_many(self, columns: Sequence[TemplateColumn]) -> list[TemplateColumn]:
        models: list[TemplateColumnModel] = []
        for column in columns:
            model = TemplateColumnModel()
            self._apply_entity_to_model(model, column, include_creation_fields=True)
            self.session.add(model)
            models.append(model)

        self.session.commit()

        for model in models:
            self.session.refresh(model)
            if model.rules:
                self.session.refresh(model, attribute_names=["rules"])

        return [self._to_entity(model) for model in models]

    def update(self, column: TemplateColumn) -> TemplateColumn:
        model = self._get_model(id=column.id)
        if not model:
            msg = f"Template column with id {column.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, column, include_creation_fields=False)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        if model.rules:
            self.session.refresh(model, attribute_names=["rules"])
        return self._to_entity(model)

    def delete(self, column_id: int, *, deleted_by: int | None = None) -> None:
        model = self._get_model(id=column_id, include_deleted=True)
        if not model:
            msg = f"Template column with id {column_id} not found"
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
    def _to_entity(model: TemplateColumnModel) -> TemplateColumn:
        return TemplateColumn(
            id=model.id,
            template_id=model.template_id,
            rule_ids=tuple(sorted(rule.id for rule in model.rules)),
            rule_header=tuple(model.rule_header) if model.rule_header else None,
            name=model.name,
            description=model.description,
            data_type=model.data_type,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_by=model.updated_by,
            updated_at=model.updated_at,
            is_active=model.is_active,
            deleted=model.deleted,
            deleted_by=model.deleted_by,
            deleted_at=model.deleted_at,
        )

    def _get_model(self, include_deleted: bool = False, **filters) -> TemplateColumnModel | None:
        query = self.session.query(TemplateColumnModel).options(
            joinedload(TemplateColumnModel.rules)
        )
        if not include_deleted:
            query = query.filter(TemplateColumnModel.deleted.is_(False))
        return query.filter_by(**filters).first()

    def _apply_entity_to_model(
        self,
        model: TemplateColumnModel,
        column: TemplateColumn,
        *,
        include_creation_fields: bool,
    ) -> None:
        if include_creation_fields:
            model.created_by = column.created_by
            model.created_at = column.created_at
            model.updated_by = None
            model.updated_at = None
        model.template_id = column.template_id
        model.rules = self._load_rules(column.rule_ids)
        model.rule_header = list(column.rule_header) if column.rule_header else None
        model.name = column.name
        model.description = column.description
        model.data_type = column.data_type
        if not include_creation_fields:
            model.updated_by = column.updated_by
            model.updated_at = column.updated_at
        model.is_active = column.is_active
        model.deleted = column.deleted
        model.deleted_by = column.deleted_by
        model.deleted_at = column.deleted_at

    def _load_rules(self, rule_ids: tuple[int, ...]) -> list[RuleModel]:
        if not rule_ids:
            return []

        unique_ids: list[int] = []
        seen: set[int] = set()
        for rule_id in rule_ids:
            if rule_id in seen:
                continue
            seen.add(rule_id)
            unique_ids.append(rule_id)
        rule_models = (
            self.session.query(RuleModel)
            .filter(RuleModel.id.in_(unique_ids))
            .all()
        )
        found = {rule.id: rule for rule in rule_models}
        missing = [rule_id for rule_id in unique_ids if rule_id not in found]
        if missing:
            missing_str = ", ".join(str(rule_id) for rule_id in missing)
            raise ValueError(f"Las reglas {missing_str} no existen")

        return [found[rule_id] for rule_id in unique_ids]

    def is_rule_in_use(self, rule_id: int) -> bool:
        """Return ``True`` when a rule is linked to any template column."""

        query = (
            self.session.query(template_column_rule_table.c.template_column_id)
            .join(
                TemplateColumnModel,
                TemplateColumnModel.id
                == template_column_rule_table.c.template_column_id,
            )
            .filter(
                template_column_rule_table.c.rule_id == rule_id,
                TemplateColumnModel.deleted.is_(False),
            )
        )
        return query.first() is not None

    def rule_used_in_published_template(self, rule_id: int) -> bool:
        """Return ``True`` if a rule is assigned to a column of a published template."""

        query = (
            self.session.query(TemplateColumnModel.id)
            .join(TemplateModel, TemplateModel.id == TemplateColumnModel.template_id)
            .join(
                template_column_rule_table,
                template_column_rule_table.c.template_column_id
                == TemplateColumnModel.id,
            )
            .filter(
                template_column_rule_table.c.rule_id == rule_id,
                TemplateColumnModel.deleted.is_(False),
                TemplateModel.status == "published",
            )
        )
        return query.first() is not None


__all__ = ["TemplateColumnRepository"]
