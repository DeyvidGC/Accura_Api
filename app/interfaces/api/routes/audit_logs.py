"""Routes for inspecting and managing audit log entries."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.application.use_cases.audit_logs import (
    delete_audit_log as delete_audit_log_uc,
    get_audit_log as get_audit_log_uc,
    list_audit_logs as list_audit_logs_uc,
)
from app.domain.entities import AuditLog, User
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import require_admin
from app.interfaces.api.schemas import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["audit_logs"])


def _audit_log_to_read_model(entry: AuditLog) -> AuditLogRead:
    if hasattr(AuditLogRead, "model_validate"):
        return AuditLogRead.model_validate(entry)
    return AuditLogRead.from_orm(entry)


@router.get("/", response_model=list[AuditLogRead])
def list_audit_logs(
    template_name: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[AuditLogRead]:
    """Return audit log entries optionally filtered by template name."""

    entries = list_audit_logs_uc(db, template_name=template_name)
    return [_audit_log_to_read_model(entry) for entry in entries]


@router.get("/{entry_id}", response_model=AuditLogRead)
def read_audit_log(
    entry_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AuditLogRead:
    """Return the audit log entry identified by ``entry_id``."""

    try:
        entry = get_audit_log_uc(db, entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _audit_log_to_read_model(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audit_log(
    entry_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    """Delete the audit log entry identified by ``entry_id``."""

    try:
        delete_audit_log_uc(db, entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
