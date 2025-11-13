"""Persistence helpers for template access assignments."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy.orm import Session

from app.domain.entities import TemplateUserAccess
from app.infrastructure.models import TemplateUserAccessModel


class TemplateUserAccessRepository:
    """Provide CRUD operations for template access records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_template(
        self,
        template_id: int,
        *,
        include_inactive: bool = False,
        include_scheduled: bool = False,
    ) -> Sequence[TemplateUserAccess]:
        query = self.session.query(TemplateUserAccessModel).filter(
            TemplateUserAccessModel.template_id == template_id
        )
        if not include_inactive:
            now = datetime.utcnow()
            filters = [
                TemplateUserAccessModel.revoked_at.is_(None),
                (
                    TemplateUserAccessModel.end_date.is_(None)
                    | (TemplateUserAccessModel.end_date >= now)
                ),
            ]
            if not include_scheduled:
                filters.append(TemplateUserAccessModel.start_date <= now)
            query = query.filter(*filters)
        query = query.order_by(TemplateUserAccessModel.start_date.desc())
        return [self._to_entity(model) for model in query.all()]

    def get(self, access_id: int) -> TemplateUserAccess | None:
        model = self.session.get(TemplateUserAccessModel, access_id)
        return self._to_entity(model) if model else None

    def get_by_template_and_user(
        self,
        *,
        template_id: int,
        user_id: int,
    ) -> TemplateUserAccess | None:
        model = (
            self.session.query(TemplateUserAccessModel)
            .filter(
                TemplateUserAccessModel.template_id == template_id,
                TemplateUserAccessModel.user_id == user_id,
                TemplateUserAccessModel.revoked_at.is_(None),
            )
            .order_by(TemplateUserAccessModel.start_date.desc())
            .first()
        )
        return self._to_entity(model) if model else None

    def get_active_access(
        self,
        *,
        user_id: int,
        template_id: int,
        reference_time: datetime | None = None,
    ) -> TemplateUserAccess | None:
        if reference_time is None:
            reference_time = datetime.utcnow()
        model = (
            self.session.query(TemplateUserAccessModel)
            .filter(
                TemplateUserAccessModel.user_id == user_id,
                TemplateUserAccessModel.template_id == template_id,
                TemplateUserAccessModel.revoked_at.is_(None),
                TemplateUserAccessModel.start_date <= reference_time,
                (
                    TemplateUserAccessModel.end_date.is_(None)
                    | (TemplateUserAccessModel.end_date >= reference_time)
                ),
            )
            .order_by(TemplateUserAccessModel.start_date.desc())
            .first()
        )
        return self._to_entity(model) if model else None

    def create(self, access: TemplateUserAccess) -> TemplateUserAccess:
        model = TemplateUserAccessModel()
        self._apply_entity_to_model(model, access, include_creation_fields=True)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def revoke(
        self,
        *,
        access_id: int,
        revoked_by: int,
        revoked_at: datetime | None = None,
    ) -> TemplateUserAccess:
        model = self.session.get(TemplateUserAccessModel, access_id)
        if model is None:
            msg = f"Template access with id {access_id} not found"
            raise ValueError(msg)
        model.revoked_by = revoked_by
        model.revoked_at = revoked_at or datetime.utcnow()
        model.updated_at = model.revoked_at
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def update(self, access: TemplateUserAccess) -> TemplateUserAccess:
        model = self.session.get(TemplateUserAccessModel, access.id)
        if model is None:
            msg = f"Template access with id {access.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, access, include_creation_fields=False)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: TemplateUserAccessModel) -> TemplateUserAccess:
        return TemplateUserAccess(
            id=model.id,
            template_id=model.template_id,
            user_id=model.user_id,
            start_date=model.start_date,
            end_date=model.end_date,
            revoked_at=model.revoked_at,
            revoked_by=model.revoked_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _apply_entity_to_model(
        model: TemplateUserAccessModel,
        access: TemplateUserAccess,
        *,
        include_creation_fields: bool,
    ) -> None:
        model.template_id = access.template_id
        model.user_id = access.user_id
        model.start_date = access.start_date
        model.end_date = access.end_date
        model.revoked_at = access.revoked_at
        model.revoked_by = access.revoked_by
        if include_creation_fields:
            model.created_at = access.created_at or datetime.utcnow()
        model.updated_at = access.updated_at or datetime.utcnow()


__all__ = ["TemplateUserAccessRepository"]
