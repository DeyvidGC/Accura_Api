"""Persistence layer for audit log records."""

from sqlalchemy.orm import Session

from app.domain.entities import AuditLog
from app.infrastructure.models import AuditLogModel


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

    @staticmethod
    def _to_entity(model: AuditLogModel) -> AuditLog:
        return AuditLog(
            id=model.id,
            template_name=model.template_name,
            columns=list(model.columns) if model.columns is not None else [],
            operation=model.operation,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_by=model.updated_by,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _apply_entity_to_model(model: AuditLogModel, entry: AuditLog) -> None:
        model.template_name = entry.template_name
        model.columns = list(entry.columns)
        model.operation = entry.operation
        model.created_by = entry.created_by
        model.created_at = entry.created_at
        model.updated_by = entry.updated_by
        model.updated_at = entry.updated_at


__all__ = ["AuditLogRepository"]
