"""Use cases for aggregating recent activity across the platform."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain.entities import (
    ActivityEvent,
    User,
    LOAD_STATUS_FAILED,
    LOAD_STATUS_PROCESSING,
    LOAD_STATUS_VALIDATED_SUCCESS,
    LOAD_STATUS_VALIDATED_WITH_ERRORS,
)
from app.infrastructure.models import (
    LoadModel,
    TemplateModel,
    TemplateUserAccessModel,
    UserModel,
    RoleModel,
)


def _safe_datetime(*candidates: datetime | None) -> datetime:
    for candidate in candidates:
        if isinstance(candidate, datetime):
            return candidate
    return datetime.utcnow()


def get_recent_activity(
    session: Session, *, current_user: User, limit: int = 20
) -> list[ActivityEvent]:
    """Return a merged list with the most recent relevant events."""

    load_query = (
        session.query(
            LoadModel.id,
            LoadModel.created_at,
            LoadModel.started_at,
            LoadModel.finished_at,
            LoadModel.status,
            LoadModel.file_name,
            TemplateModel.id.label("template_id"),
            TemplateModel.name.label("template_name"),
            UserModel.id.label("user_id"),
            UserModel.name.label("user_name"),
        )
        .join(TemplateModel, LoadModel.template_id == TemplateModel.id)
        .join(UserModel, LoadModel.user_id == UserModel.id)
    )
    access_query = (
        session.query(
            TemplateUserAccessModel.id,
            TemplateUserAccessModel.created_at,
            TemplateUserAccessModel.start_date,
            TemplateModel.id.label("template_id"),
            TemplateModel.name.label("template_name"),
            UserModel.id.label("user_id"),
            UserModel.name.label("user_name"),
        )
        .join(TemplateModel, TemplateUserAccessModel.template_id == TemplateModel.id)
        .join(UserModel, TemplateUserAccessModel.user_id == UserModel.id)
    )
    user_query = (
        session.query(
            UserModel.id,
            UserModel.created_at,
            UserModel.name,
            UserModel.email,
            RoleModel.name.label("role_name"),
            RoleModel.alias.label("role_alias"),
        )
        .join(RoleModel, UserModel.role_id == RoleModel.id)
        .filter(UserModel.deleted.is_(False))
    )

    if current_user.is_admin():
        load_query = load_query.filter(
            or_(
                LoadModel.user_id == current_user.id,
                UserModel.created_by == current_user.id,
            )
        )
        access_query = access_query.filter(
            or_(
                TemplateModel.created_by == current_user.id,
                UserModel.created_by == current_user.id,
                UserModel.id == current_user.id,
            )
        )
        user_query = user_query.filter(UserModel.created_by == current_user.id)
    else:
        load_query = load_query.filter(LoadModel.user_id == current_user.id)
        access_query = access_query.filter(
            TemplateUserAccessModel.user_id == current_user.id
        )
        user_query = user_query.filter(UserModel.id == current_user.id)

    load_rows = (
        load_query.order_by(LoadModel.created_at.desc())
        .limit(limit)
        .all()
    )

    access_rows = (
        access_query.order_by(TemplateUserAccessModel.created_at.desc())
        .limit(limit)
        .all()
    )

    user_rows = (
        user_query.order_by(UserModel.created_at.desc())
        .limit(limit)
        .all()
    )

    events: list[ActivityEvent] = []

    for row in load_rows:
        created_at = _safe_datetime(row.created_at, row.started_at)
        processing_summary = (
            f"{row.user_name} inició la carga del archivo '{row.file_name}' "
            f"en la plantilla '{row.template_name}'. Estado: {LOAD_STATUS_PROCESSING}."
        )
        events.append(
            ActivityEvent(
                event_id=f"load-{row.id}",
                event_type="load.uploaded",
                summary=processing_summary,
                created_at=created_at,
                metadata={
                    "load_id": row.id,
                    "template_id": row.template_id,
                    "template_name": row.template_name,
                    "user_id": row.user_id,
                    "user_name": row.user_name,
                    "file_name": row.file_name,
                    "status": LOAD_STATUS_PROCESSING,
                    "stage": "processing",
                    "created_at": row.created_at,
                    "started_at": row.started_at,
                },
            )
        )

        finished_at = _safe_datetime(row.finished_at) if row.finished_at else None
        status = row.status
        if finished_at and status:
            if status == LOAD_STATUS_VALIDATED_SUCCESS:
                event_type = "load.completed.success"
                summary = (
                    f"{row.user_name} completó la validación del archivo "
                    f"'{row.file_name}' para la plantilla '{row.template_name}'. "
                    f"Estado final: {status}."
                )
            elif status == LOAD_STATUS_VALIDATED_WITH_ERRORS:
                event_type = "load.completed.errors"
                summary = (
                    f"{row.user_name} finalizó la validación del archivo "
                    f"'{row.file_name}' para la plantilla '{row.template_name}' "
                    f"con observaciones. Estado final: {status}."
                )
            elif status == LOAD_STATUS_FAILED:
                event_type = "load.completed.failed"
                summary = (
                    f"{row.user_name} no pudo validar el archivo '{row.file_name}' "
                    f"para la plantilla '{row.template_name}'. Estado final: {status}."
                )
            else:
                event_type = "load.completed"
                summary = (
                    f"{row.user_name} finalizó la carga del archivo '{row.file_name}' "
                    f"para la plantilla '{row.template_name}'. Estado final: {status}."
                )

            events.append(
                ActivityEvent(
                    event_id=f"load-{row.id}-completed",
                    event_type=event_type,
                    summary=summary,
                    created_at=finished_at,
                    metadata={
                        "load_id": row.id,
                        "template_id": row.template_id,
                        "template_name": row.template_name,
                        "user_id": row.user_id,
                        "user_name": row.user_name,
                        "file_name": row.file_name,
                        "status": status,
                        "stage": "completed",
                        "created_at": row.created_at,
                        "started_at": row.started_at,
                        "finished_at": row.finished_at,
                    },
                )
            )

    for row in access_rows:
        created_at = _safe_datetime(row.created_at, row.start_date)
        summary = (
            f"{row.user_name} recibió acceso a la plantilla '{row.template_name}'."
        )
        events.append(
            ActivityEvent(
                event_id=f"access-{row.id}",
                event_type="template.access.granted",
                summary=summary,
                created_at=created_at,
                metadata={
                    "access_id": row.id,
                    "template_id": row.template_id,
                    "template_name": row.template_name,
                    "user_id": row.user_id,
                    "user_name": row.user_name,
                },
            )
        )

    for row in user_rows:
        created_at = _safe_datetime(row.created_at)
        summary = (
            f"Se creó el usuario '{row.name}' con el rol '{row.role_name}'."
        )
        events.append(
            ActivityEvent(
                event_id=f"user-{row.id}",
                event_type="user.created",
                summary=summary,
                created_at=created_at,
                metadata={
                    "user_id": row.id,
                    "name": row.name,
                    "email": row.email,
                    "role_name": row.role_name,
                    "role_alias": row.role_alias,
                },
            )
        )

    events.sort(key=lambda event: event.created_at, reverse=True)
    return events[:limit]


__all__ = ["get_recent_activity"]
