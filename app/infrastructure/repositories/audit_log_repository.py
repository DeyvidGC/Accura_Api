"""Persistence layer for audit log records."""

from typing import Iterable

from sqlalchemy.orm import Session

from app.domain.entities import AuditLog
from app.infrastructure.models import AuditLogModel
from app.utils import (
    ensure_app_naive_datetime,
    ensure_app_timezone,
    now_in_app_timezone,
)


class AuditLogRepository:
    """Provide CRUD helpers for :class:`AuditLog` entries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entry: AuditLog) -> AuditLog:
        model = AuditLogModel()
        self._apply_entity_to_model(model, entry)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def get(self, entry_id: int) -> AuditLog | None:
        """Return an audit entry by its primary key, if present."""

        model = self.session.get(AuditLogModel, entry_id)
        if model is None:
            return None
        return self._to_entity(model)

    def list(self, *, template_name: str | None = None) -> list[AuditLog]:
        """Return audit entries, optionally filtered by template name."""

        query = self.session.query(AuditLogModel)
        if template_name is not None:
            query = query.filter(AuditLogModel.template_name == template_name)

        models: Iterable[AuditLogModel] = query.order_by(AuditLogModel.id).all()
        return [self._to_entity(model) for model in models]

    def delete(self, entry_id: int) -> bool:
        """Delete an audit entry by id.

        Returns ``True`` when a record was removed and ``False`` when the
        requested entry was not found.
        """

        model = self.session.get(AuditLogModel, entry_id)
        if model is None:
            return False

        self.session.delete(model)
        self.session.commit()
        return True

    @staticmethod
    def _to_entity(model: AuditLogModel) -> AuditLog:
        return AuditLog(
            id=model.id,
            template_name=model.template_name,
            columns=list(model.columns) if model.columns is not None else [],
            operation=model.operation,
            created_by=model.created_by,
            created_at=ensure_app_timezone(model.created_at),
            updated_by=model.updated_by,
            updated_at=ensure_app_timezone(model.updated_at),
        )

    @staticmethod
    def _apply_entity_to_model(model: AuditLogModel, entry: AuditLog) -> None:
        model.template_name = entry.template_name
        model.columns = list(entry.columns)
        model.operation = entry.operation
        model.created_by = entry.created_by
        model.created_at = (
            ensure_app_naive_datetime(entry.created_at)
            or ensure_app_naive_datetime(now_in_app_timezone())
        )
        model.updated_by = entry.updated_by
        model.updated_at = ensure_app_naive_datetime(entry.updated_at)


__all__ = ["AuditLogRepository"]
