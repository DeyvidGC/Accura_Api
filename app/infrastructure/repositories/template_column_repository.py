"""Persistence layer for template columns."""

from collections.abc import Sequence

from sqlalchemy.orm import Session, joinedload

from app.domain.entities import TemplateColumn
from app.infrastructure.models import TemplateColumnModel


class TemplateColumnRepository:
    """Provide CRUD operations for template columns."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_template(self, template_id: int) -> Sequence[TemplateColumn]:
        query = (
            self.session.query(TemplateColumnModel)
            .options(joinedload(TemplateColumnModel.rule))
            .filter(TemplateColumnModel.template_id == template_id)
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
        if model.rule is None and column.rule_id is not None:
            self.session.refresh(model, attribute_names=["rule"])
        return self._to_entity(model)

    def update(self, column: TemplateColumn) -> TemplateColumn:
        model = self._get_model(id=column.id)
        if not model:
            msg = f"Template column with id {column.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, column, include_creation_fields=False)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        if model.rule is None and column.rule_id is not None:
            self.session.refresh(model, attribute_names=["rule"])
        return self._to_entity(model)

    def delete(self, column_id: int) -> None:
        model = self._get_model(id=column_id)
        if not model:
            msg = f"Template column with id {column_id} not found"
            raise ValueError(msg)
        self.session.delete(model)
        self.session.commit()

    @staticmethod
    def _to_entity(model: TemplateColumnModel) -> TemplateColumn:
        return TemplateColumn(
            id=model.id,
            template_id=model.template_id,
            rule_id=model.rule_id,
            name=model.name,
            description=model.description,
            data_type=model.data_type,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_by=model.updated_by,
            updated_at=model.updated_at,
            is_active=model.is_active,
        )

    def _get_model(self, **filters) -> TemplateColumnModel | None:
        query = self.session.query(TemplateColumnModel).options(
            joinedload(TemplateColumnModel.rule)
        )
        return query.filter_by(**filters).first()

    @staticmethod
    def _apply_entity_to_model(
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
        model.rule_id = column.rule_id
        model.name = column.name
        model.description = column.description
        model.data_type = column.data_type
        if not include_creation_fields:
            model.updated_by = column.updated_by
            model.updated_at = column.updated_at
        model.is_active = column.is_active


__all__ = ["TemplateColumnRepository"]
