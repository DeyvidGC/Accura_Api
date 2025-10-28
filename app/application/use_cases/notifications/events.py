"""Utility helpers to generate and dispatch domain notifications."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.domain.entities import (
    LOAD_STATUS_PROCESSING,
    LOAD_STATUS_VALIDATED_SUCCESS,
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
    recipient_id: int,
    event_type: str,
    title: str,
    message: str,
    payload: dict | None = None,
) -> Notification:
    notification = Notification(
        id=None,
        recipient_id=recipient_id,
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


def _admin_recipient_ids(session: Session) -> list[int]:
    return UserRepository(session).list_ids_by_role_alias(_ADMIN_ROLE_ALIAS)


def notify_template_created(session: Session, *, template: Template) -> None:
    """Notify administrators that a new template has been created."""

    recipients = _admin_recipient_ids(session)
    message = f"Se creó la plantilla '{template.name}'."
    for recipient_id in recipients:
        _persist_notification(
            session,
            recipient_id=recipient_id,
            event_type="template.created",
            title="Nueva plantilla",
            message=message,
            payload={"template_id": template.id, "status": template.status},
        )


def notify_template_published(session: Session, *, template: Template) -> None:
    """Notify administrators that a template has been published."""

    recipients = _admin_recipient_ids(session)
    if not recipients:
        return
    message = f"La plantilla '{template.name}' fue publicada."
    for recipient_id in recipients:
        _persist_notification(
            session,
            recipient_id=recipient_id,
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
        recipient_id=user.id,
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
        recipient_id=user.id,
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
    """Inform administrators that a load finished with a successful validation."""

    recipients = _admin_recipient_ids(session)
    if not recipients:
        return
    message = (
        f"La carga '{load.file_name}' de la plantilla '{template.name}' "
        "finalizó con validación exitosa."
    )
    payload = {
        "template_id": template.id,
        "load_id": load.id,
        "status": LOAD_STATUS_VALIDATED_SUCCESS,
    }
    for recipient_id in recipients:
        _persist_notification(
            session,
            recipient_id=recipient_id,
            event_type="load.validated.success",
            title="Validación exitosa",
            message=message,
            payload=payload,
        )


__all__ = [
    "notify_template_created",
    "notify_template_published",
    "notify_template_processing",
    "notify_template_access_granted",
    "notify_load_validated_success",
]
