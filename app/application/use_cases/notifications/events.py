"""Utility helpers to generate and dispatch domain notifications."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.domain.entities import (
    LOAD_STATUS_FAILED,
    LOAD_STATUS_PROCESSING,
    LOAD_STATUS_VALIDATED_SUCCESS,
    LOAD_STATUS_VALIDATED_WITH_ERRORS,
    Load,
    Notification,
    Template,
    TemplateUserAccess,
    User,
)
from app.infrastructure.notifications import dispatch_notification
from app.infrastructure.repositories import NotificationRepository, UserRepository

_ADMIN_ROLE_ALIAS = "admin"


def _persist_notification(
    session: Session,
    *,
    user_id: int,
    event_type: str,
    title: str,
    message: str,
    payload: dict | None = None,
) -> Notification:
    notification = Notification(
        id=None,
        user_id=user_id,
        event_type=event_type,
        title=title,
        message=message,
        payload=payload or {},
        created_at=datetime.utcnow(),
        read_at=None,
    )
    repository = NotificationRepository(session)
    saved = repository.create(notification)
    dispatch_notification(saved)
    return saved


def _admin_user_ids(session: Session) -> list[int]:
    return UserRepository(session).list_ids_by_role_alias(_ADMIN_ROLE_ALIAS)


def notify_template_created(session: Session, *, template: Template) -> None:
    """Notify administrators that a new template has been created."""

    user_ids = _admin_user_ids(session)
    message = f"Se creó la plantilla '{template.name}'."
    for user_id in user_ids:
        _persist_notification(
            session,
            user_id=user_id,
            event_type="template.created",
            title="Nueva plantilla",
            message=message,
            payload={"template_id": template.id, "status": template.status},
        )


def notify_template_published(session: Session, *, template: Template) -> None:
    """Notify administrators that a template has been published."""

    user_ids = _admin_user_ids(session)
    if not user_ids:
        return
    message = f"La plantilla '{template.name}' fue publicada."
    for user_id in user_ids:
        _persist_notification(
            session,
            user_id=user_id,
            event_type="template.published",
            title="Plantilla publicada",
            message=message,
            payload={"template_id": template.id, "status": template.status},
        )


def notify_template_processing(
    session: Session,
    *,
    load: Load,
    template: Template,
    user: User,
) -> None:
    """Inform the load owner that processing has started."""

    message = (
        f"Tu carga '{load.file_name}' para la plantilla '{template.name}' "
        f"ha iniciado el procesamiento."
    )
    _persist_notification(
        session,
        user_id=user.id,
        event_type="load.processing",
        title="Procesamiento iniciado",
        message=message,
        payload={
            "template_id": template.id,
            "load_id": load.id,
            "status": LOAD_STATUS_PROCESSING,
        },
    )


def notify_template_access_granted(
    session: Session,
    *,
    access: TemplateUserAccess,
    template: Template,
    user: User,
) -> None:
    """Notify a user that they gained access to a template."""

    message = f"Se te otorgó acceso a la plantilla '{template.name}'."
    payload = {
        "template_id": template.id,
        "access_id": access.id,
        "access_start": access.start_date.isoformat() if access.start_date else None,
        "access_end": access.end_date.isoformat() if access.end_date else None,
    }
    _persist_notification(
        session,
        user_id=user.id,
        event_type="template.access.granted",
        title="Acceso a plantilla",
        message=message,
        payload=payload,
    )


def notify_load_validated_success(
    session: Session,
    *,
    load: Load,
    template: Template,
) -> None:
    """Inform administrators that a load finished validation and report its status."""

    user_ids = _admin_user_ids(session)
    if not user_ids:
        return

    status = load.status
    if status == LOAD_STATUS_VALIDATED_SUCCESS:
        event_type = "load.validated.success"
        title = "Validación exitosa"
        message_detail = "finalizó con validación exitosa"
    elif status == LOAD_STATUS_VALIDATED_WITH_ERRORS:
        event_type = "load.validated.errors"
        title = "Validación con observaciones"
        message_detail = "finalizó con observaciones de validación"
    else:
        return

    message = (
        f"La carga '{load.file_name}' de la plantilla '{template.name}' "
        f"{message_detail}."
    )
    payload = {
        "template_id": template.id,
        "load_id": load.id,
        "status": status,
    }
    for user_id in user_ids:
        _persist_notification(
            session,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            payload=payload,
        )


def notify_load_status_changed(
    session: Session,
    *,
    load: Load,
    template: Template,
    user: User,
) -> None:
    """Notify the load owner about a status change once processing completes."""

    status = load.status
    if status == LOAD_STATUS_VALIDATED_SUCCESS:
        event_type = "load.completed.success"
        title = "Carga validada"
        message = (
            f"Tu carga '{load.file_name}' para la plantilla '{template.name}' "
            "finalizó exitosamente."
        )
    elif status == LOAD_STATUS_VALIDATED_WITH_ERRORS:
        event_type = "load.completed.errors"
        title = "Carga con observaciones"
        message = (
            f"Tu carga '{load.file_name}' para la plantilla '{template.name}' "
            "finalizó con observaciones."
        )
    elif status == LOAD_STATUS_FAILED:
        event_type = "load.completed.failed"
        title = "Carga fallida"
        message = (
            f"Tu carga '{load.file_name}' para la plantilla '{template.name}' "
            "no pudo completarse."
        )
    else:
        return

    payload = {
        "template_id": template.id,
        "load_id": load.id,
        "status": status,
        "total_rows": load.total_rows,
        "error_rows": load.error_rows,
    }
    _persist_notification(
        session,
        user_id=user.id,
        event_type=event_type,
        title=title,
        message=message,
        payload=payload,
    )


__all__ = [
    "notify_template_created",
    "notify_template_published",
    "notify_template_processing",
    "notify_template_access_granted",
    "notify_load_status_changed",
    "notify_load_validated_success",
]
