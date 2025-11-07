"""Use cases for aggregating recent activity across the platform."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain.entities import ActivityEvent, User
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
        created_at = _safe_datetime(row.created_at)
        summary = (
            f"{row.user_name} cargó '{row.file_name}' en la plantilla "
            f"'{row.template_name}'."
        )
        events.append(
            ActivityEvent(
                event_id=f"load-{row.id}",
                event_type="load.uploaded",
                summary=summary,
                created_at=created_at,
                metadata={
                    "load_id": row.id,
                    "template_id": row.template_id,
                    "template_name": row.template_name,
                    "user_id": row.user_id,
                    "user_name": row.user_name,
                    "file_name": row.file_name,
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
