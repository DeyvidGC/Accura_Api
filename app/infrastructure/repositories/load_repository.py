"""Persistence layer for template data load records."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.entities import Load
from app.infrastructure.models import LoadModel


class LoadRepository:
    """Provide CRUD-style operations for :class:`Load` records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        user_id: int | None = None,
        template_id: int | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> Sequence[Load]:
        query = self.session.query(LoadModel)
        if user_id is not None:
            query = query.filter(LoadModel.user_id == user_id)
        if template_id is not None:
            query = query.filter(LoadModel.template_id == template_id)
        query = query.order_by(LoadModel.created_at.desc(), LoadModel.id.desc())
        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def get(self, load_id: int) -> Load | None:
        model = self.session.get(LoadModel, load_id)
        return self._to_entity(model) if model else None

    def create(self, load: Load) -> Load:
        model = LoadModel()
        self._apply_entity_to_model(model, load, include_creation_fields=True)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def update(self, load: Load) -> Load:
        model = self.session.get(LoadModel, load.id)
        if model is None:
            msg = f"Load with id {load.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, load, include_creation_fields=False)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def count_completed_by_user_and_template(
        self, *, user_id: int, template_id: int
    ) -> int:
        """Return the number of completed loads for ``user_id`` and ``template_id``."""

        total = (
            self.session.query(func.count(LoadModel.id))
            .filter(
                LoadModel.user_id == user_id,
                LoadModel.template_id == template_id,
                LoadModel.status == "completed",
            )
            .scalar()
        )
        return int(total or 0)

    @staticmethod
    def _to_entity(model: LoadModel) -> Load:
        return Load(
            id=model.id,
            template_id=model.template_id,
            user_id=model.user_id,
            status=model.status,
            file_name=model.file_name,
            total_rows=model.total_rows,
            error_rows=model.error_rows,
            report_path=model.report_path,
            created_at=model.created_at,
            started_at=model.started_at,
            finished_at=model.finished_at,
        )

    @staticmethod
    def _apply_entity_to_model(
        model: LoadModel,
        load: Load,
        *,
        include_creation_fields: bool,
    ) -> None:
        model.template_id = load.template_id
        model.user_id = load.user_id
        model.status = load.status
        model.file_name = load.file_name
        model.total_rows = load.total_rows
        model.error_rows = load.error_rows
        model.report_path = load.report_path
        if include_creation_fields:
            model.created_at = load.created_at or datetime.utcnow()
        model.started_at = load.started_at
        model.finished_at = load.finished_at


__all__ = ["LoadRepository"]
