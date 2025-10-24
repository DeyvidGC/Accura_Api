"""Persistence layer for templates."""

from collections.abc import Sequence

from sqlalchemy.orm import Session, joinedload

from app.domain.entities import Template, TemplateColumn
from app.infrastructure.models import TemplateModel


class TemplateRepository:
    """Provide CRUD operations for templates."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, skip: int = 0, limit: int = 100) -> Sequence[Template]:
        query = (
            self.session.query(TemplateModel)
            .options(joinedload(TemplateModel.columns))
            .offset(skip)
            .limit(limit)
        )
        return [self._to_entity(model) for model in query.all()]

    def get(self, template_id: int) -> Template | None:
        model = self._get_model(id=template_id)
        return self._to_entity(model) if model else None

    def get_by_table_name(self, table_name: str) -> Template | None:
        model = self._get_model(table_name=table_name)
        return self._to_entity(model) if model else None

    def create(self, template: Template) -> Template:
        model = TemplateModel()
        self._apply_entity_to_model(model, template, include_creation_fields=True)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        if not self._relationship_loaded(model):
            self.session.refresh(model, attribute_names=["columns"])
        return self._to_entity(model)

    def update(self, template: Template) -> Template:
        model = self._get_model(id=template.id)
        if not model:
            msg = f"Template with id {template.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, template, include_creation_fields=False)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        if not self._relationship_loaded(model):
            self.session.refresh(model, attribute_names=["columns"])
        return self._to_entity(model)

    def delete(self, template_id: int) -> None:
        model = self._get_model(id=template_id)
        if not model:
            msg = f"Template with id {template_id} not found"
            raise ValueError(msg)
        self.session.delete(model)
        self.session.commit()

    def _get_model(self, **filters) -> TemplateModel | None:
        query = self.session.query(TemplateModel).options(
            joinedload(TemplateModel.columns)
        )
        return query.filter_by(**filters).first()

    @staticmethod
    def _to_entity(model: TemplateModel) -> Template:
        columns = [TemplateRepository._column_to_entity(col) for col in model.columns]
        return Template(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            status=model.status,
            description=model.description,
            table_name=model.table_name,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_by=model.updated_by,
            updated_at=model.updated_at,
            is_active=model.is_active,
            columns=columns,
        )

    @staticmethod
    def _column_to_entity(model) -> TemplateColumn:
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

    @staticmethod
    def _apply_entity_to_model(
        model: TemplateModel,
        template: Template,
        *,
        include_creation_fields: bool,
    ) -> None:
        if include_creation_fields:
            model.created_by = template.created_by
            model.created_at = template.created_at
            model.updated_by = None
            model.updated_at = None
        model.user_id = template.user_id
        model.name = template.name
        model.status = template.status
        model.description = template.description
        model.table_name = template.table_name
        if not include_creation_fields:
            model.updated_by = template.updated_by
            model.updated_at = template.updated_at
        model.is_active = template.is_active

    @staticmethod
    def _relationship_loaded(model: TemplateModel) -> bool:
        try:
            return model.columns is not None
        except Exception:  # pragma: no cover - fallback for unloaded relationship
            return False


__all__ = ["TemplateRepository"]
