"""Use cases for interacting with audit log entries."""

from sqlalchemy.orm import Session

from app.domain.entities import AuditLog
from app.infrastructure.repositories import AuditLogRepository


def list_audit_logs(
    session: Session, *, template_name: str | None = None
) -> list[AuditLog]:
    """Return audit log entries optionally filtered by template name."""

    repository = AuditLogRepository(session)
    return repository.list(template_name=template_name)


def get_audit_log(session: Session, entry_id: int) -> AuditLog:
    """Return an audit log entry identified by ``entry_id`` or raise an error."""

    repository = AuditLogRepository(session)
    entry = repository.get(entry_id)
    if entry is None:
        raise ValueError("Registro de auditoría no encontrado")
    return entry


def delete_audit_log(session: Session, entry_id: int) -> None:
    """Remove an audit log entry or raise an error if it does not exist."""

    repository = AuditLogRepository(session)
    if not repository.delete(entry_id):
        raise ValueError("Registro de auditoría no encontrado")


__all__ = [
    "list_audit_logs",
    "get_audit_log",
    "delete_audit_log",
]
