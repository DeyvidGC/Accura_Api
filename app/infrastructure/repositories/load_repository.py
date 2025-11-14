"""Persistence layer for template data load records."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import false, func, or_
from sqlalchemy.orm import Session, joinedload

from app.domain.entities import (
    LOAD_STATUS_VALIDATED_SUCCESS,
    LOAD_STATUS_VALIDATED_WITH_ERRORS,
    Load,
    Template,
    User,
)
from app.infrastructure.models import (
    LoadModel,
    TemplateColumnModel,
    TemplateModel,
    UserModel,
)
from app.infrastructure.repositories.template_repository import TemplateRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.utils import ensure_app_timezone, now_in_app_timezone

_COMPLETED_STATUSES = (
    LOAD_STATUS_VALIDATED_SUCCESS,
    LOAD_STATUS_VALIDATED_WITH_ERRORS,
)


class LoadRepository:
    """Provide CRUD-style operations for :class:`Load` records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        user_id: int | None = None,
        creator_id: int | None = None,
        template_id: int | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> Sequence[Load]:
        query = self.session.query(LoadModel)
        if user_id is not None:
            query = query.filter(LoadModel.user_id == user_id)
        if creator_id is not None:
            query = query.filter(
                or_(
                    LoadModel.user_id == creator_id,
                    LoadModel.user.has(UserModel.created_by == creator_id),
                )
            )
        if template_id is not None:
            query = query.filter(LoadModel.template_id == template_id)
        query = query.order_by(LoadModel.created_at.desc(), LoadModel.id.desc())
        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def list_with_templates(
        self,
        *,
        user_id: int | None = None,
        creator_id: int | None = None,
        template_id: int | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> Sequence[tuple[Load, Template, User]]:
        query = (
            self.session.query(LoadModel)
            .options(
                joinedload(LoadModel.template),
                joinedload(LoadModel.user).joinedload(UserModel.role),
            )
            .join(TemplateModel, LoadModel.template_id == TemplateModel.id)
            .filter(TemplateModel.deleted == false())
        )
        if user_id is not None:
            query = query.filter(LoadModel.user_id == user_id)
        if creator_id is not None:
            query = query.filter(
                or_(
                    LoadModel.user_id == creator_id,
                    LoadModel.user.has(UserModel.created_by == creator_id),
                )
            )
        if template_id is not None:
            query = query.filter(LoadModel.template_id == template_id)
        query = query.order_by(LoadModel.created_at.desc(), LoadModel.id.desc())
        if skip:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)

        pairs: list[tuple[Load, Template, User]] = []
        for model in query.all():
            template_model = model.template
            user_model = model.user
            if template_model is None or user_model is None:
                continue
            load = self._to_entity(model)
            template = self._template_summary_to_entity(template_model)
            user = self._user_summary_to_entity(user_model)
            pairs.append((load, template, user))
        return pairs

    def get(self, load_id: int) -> Load | None:
        model = self.session.get(LoadModel, load_id)
        return self._to_entity(model) if model else None

    def get_with_template(self, load_id: int) -> tuple[Load, Template] | None:
        model = (
            self.session.query(LoadModel)
            .options(
                joinedload(LoadModel.template)
                .joinedload(TemplateModel.columns)
                .joinedload(TemplateColumnModel.rules)
            )
            .filter(LoadModel.id == load_id)
            .first()
        )
        if model is None or model.template is None:
            return None
        load = self._to_entity(model)
        template = TemplateRepository._to_entity(model.template)
        return load, template

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
                LoadModel.status.in_(_COMPLETED_STATUSES),
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
            created_at=ensure_app_timezone(model.created_at),
            started_at=ensure_app_timezone(model.started_at),
            finished_at=ensure_app_timezone(model.finished_at),
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
            model.created_at = (
                ensure_app_timezone(load.created_at) or now_in_app_timezone()
            )
        model.started_at = ensure_app_timezone(load.started_at)
        model.finished_at = ensure_app_timezone(load.finished_at)

    @staticmethod
    def _template_summary_to_entity(model: TemplateModel) -> Template:
        return Template(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            status=model.status,
            description=model.description,
            table_name=model.table_name,
            created_by=model.created_by,
            created_at=ensure_app_timezone(model.created_at),
            updated_by=model.updated_by,
            updated_at=ensure_app_timezone(model.updated_at),
            is_active=model.is_active,
            deleted=model.deleted,
            deleted_by=model.deleted_by,
            deleted_at=ensure_app_timezone(model.deleted_at),
            columns=[],
        )

    @staticmethod
    def _user_summary_to_entity(model: UserModel) -> User:
        return UserRepository._to_entity(model)


__all__ = ["LoadRepository"]
