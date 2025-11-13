"""Helpers to broadcast realtime updates for load history events."""

from __future__ import annotations

from typing import Any, Iterable

from app.domain.entities import Load, Template, User
from app.infrastructure.notifications import dispatch_realtime_event

_EVENT_TYPE = "load.history"


def broadcast_load_processing_event(
    *, load: Load, template: Template, user: User
) -> None:
    """Broadcast a realtime event indicating a load entered processing."""

    _broadcast_load_event("created", load=load, template=template, user=user)


def broadcast_load_status_event(
    *, load: Load, template: Template, user: User
) -> None:
    """Broadcast a realtime event reflecting the latest status for a load."""

    _broadcast_load_event("updated", load=load, template=template, user=user)


def _broadcast_load_event(
    action: str, *, load: Load, template: Template, user: User
) -> None:
    recipients = _collect_recipient_ids(template=template, user=user)
    if not recipients:
        return

    payload = {
        "action": action,
        "status": load.status,
        "load": _serialize_load(load),
        "template": _serialize_template(template),
        "user": _serialize_user(user),
    }

    dispatch_realtime_event(recipients, event_type=_EVENT_TYPE, payload=payload)


def _collect_recipient_ids(*, template: Template, user: User) -> list[int]:
    candidates: Iterable[int | None] = (
        user.id,
        user.created_by,
        template.user_id,
        template.created_by,
    )
    unique: list[int] = []
    for candidate in candidates:
        if isinstance(candidate, int) and candidate > 0 and candidate not in unique:
            unique.append(candidate)
    return unique


def _serialize_load(load: Load) -> dict[str, Any]:
    return {
        "id": load.id,
        "template_id": load.template_id,
        "user_id": load.user_id,
        "status": load.status,
        "file_name": load.file_name,
        "total_rows": load.total_rows,
        "error_rows": load.error_rows,
        "report_path": load.report_path,
        "created_at": load.created_at.isoformat() if load.created_at else None,
        "started_at": load.started_at.isoformat() if load.started_at else None,
        "finished_at": load.finished_at.isoformat() if load.finished_at else None,
    }


def _serialize_template(template: Template) -> dict[str, Any]:
    return {
        "id": template.id,
        "user_id": template.user_id,
        "name": template.name,
        "status": template.status,
        "description": template.description,
        "table_name": template.table_name,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        "is_active": template.is_active,
        "deleted": template.deleted,
        "deleted_by": template.deleted_by,
        "deleted_at": template.deleted_at.isoformat() if template.deleted_at else None,
    }


def _serialize_user(user: User) -> dict[str, Any]:
    summary = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }
    if user.role:
        summary["role"] = {
            "id": user.role.id,
            "name": user.role.name,
            "alias": user.role.alias,
        }
    return summary


__all__ = [
    "broadcast_load_processing_event",
    "broadcast_load_status_event",
]

