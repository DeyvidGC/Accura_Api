"""Realtime helpers for broadcasting load history updates."""

from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy.orm import Session

from app.domain.entities import Load, Template, User
from app.infrastructure.notifications import dispatch_realtime_event
from app.infrastructure.repositories import LoadRepository, UserRepository

_EVENT_TYPE = "load.history"
_HISTORY_LIMIT = 100


def broadcast_load_history_processing(
    session: Session, *, load: Load, template: Template, user: User
) -> None:
    """Broadcast an event indicating that ``load`` entered processing."""

    _broadcast_history_snapshot(
        session,
        load=load,
        template=template,
        owner=user,
        change_type="created",
    )


def broadcast_load_history_status(
    session: Session, *, load: Load, template: Template, user: User
) -> None:
    """Broadcast an event reflecting the latest status for ``load``."""

    _broadcast_history_snapshot(
        session,
        load=load,
        template=template,
        owner=user,
        change_type="updated",
    )


def _broadcast_history_snapshot(
    session: Session,
    *,
    load: Load,
    template: Template,
    owner: User,
    change_type: str,
) -> None:
    recipients = _collect_recipient_ids(template=template, owner=owner)
    if not recipients:
        return

    user_repo = UserRepository(session)
    recipient_map = user_repo.get_map_by_ids(recipients)
    if not recipient_map:
        return

    load_repo = LoadRepository(session)
    for recipient_id, recipient in recipient_map.items():
        if not recipient.is_active or recipient.deleted:
            continue

        history = _history_for_recipient(load_repo, recipient)
        payload = {
            "change_type": change_type,
            "focus_load_id": load.id,
            "history": history,
        }
        dispatch_realtime_event([recipient_id], event_type=_EVENT_TYPE, payload=payload)


def _history_for_recipient(
    repository: LoadRepository, recipient: User
) -> list[dict[str, object]]:
    entries: Sequence[tuple[Load, Template, User]]
    if recipient.is_admin():
        entries = repository.list_with_templates(
            creator_id=recipient.id, skip=0, limit=_HISTORY_LIMIT
        )
    else:
        entries = repository.list_with_templates(
            user_id=recipient.id, skip=0, limit=_HISTORY_LIMIT
        )
    return [_serialize_history_entry(load, template, owner) for load, template, owner in entries]


def _collect_recipient_ids(*, template: Template, owner: User) -> list[int]:
    candidates: Iterable[int | None] = (
        owner.id,
        owner.created_by,
        template.user_id,
        template.created_by,
    )
    unique: list[int] = []
    for candidate in candidates:
        if isinstance(candidate, int) and candidate > 0 and candidate not in unique:
            unique.append(candidate)
    return unique


def _serialize_history_entry(
    load: Load, template: Template, owner: User
) -> dict[str, object]:
    return {
        "load": _serialize_load(load),
        "template": _serialize_template(template),
        "user": _serialize_user(owner),
    }


def _serialize_load(load: Load) -> dict[str, object]:
    return {
        "id": load.id,
        "template_id": load.template_id,
        "user_id": load.user_id,
        "status": load.status,
        "file_name": load.file_name,
        "total_rows": load.total_rows,
        "error_rows": load.error_rows,
        "report_path": load.report_path,
        "created_at": _iso_or_none(load.created_at),
        "started_at": _iso_or_none(load.started_at),
        "finished_at": _iso_or_none(load.finished_at),
    }


def _serialize_template(template: Template) -> dict[str, object]:
    return {
        "id": template.id,
        "user_id": template.user_id,
        "name": template.name,
        "status": template.status,
        "description": template.description,
        "table_name": template.table_name,
        "created_at": _iso_or_none(template.created_at),
        "updated_at": _iso_or_none(template.updated_at),
        "is_active": template.is_active,
        "deleted": template.deleted,
        "deleted_by": template.deleted_by,
        "deleted_at": _iso_or_none(template.deleted_at),
    }


def _serialize_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }


def _iso_or_none(value) -> str | None:
    return value.isoformat() if value else None


__all__ = [
    "broadcast_load_history_processing",
    "broadcast_load_history_status",
]
