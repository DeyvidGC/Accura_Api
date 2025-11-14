"""Utility helpers to generate and dispatch domain notifications."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.entities import (
    LOAD_STATUS_FAILED,
    LOAD_STATUS_PROCESSING,
    LOAD_STATUS_VALIDATED_SUCCESS,
    LOAD_STATUS_VALIDATED_WITH_ERRORS,
    Load,
    LoadEvent,
    LoadEventLoad,
    LoadEventTemplateSummary,
    LoadEventUserSummary,
    Notification,
    Template,
    TemplateUserAccess,
    User,
)
from app.infrastructure.notifications import dispatch_notification, dispatch_load_event
from app.infrastructure.repositories import NotificationRepository, UserRepository
from app.utils import ensure_app_timezone, now_in_app_timezone

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
        created_at=now_in_app_timezone(),
        read_at=None,
    )
    repository = NotificationRepository(session)
    saved = repository.create(notification)
    dispatch_notification(saved)
    return saved


def _load_event_recipients(template: Template, user: User) -> set[int]:
    """Return the set of user identifiers that should receive load events."""

    recipients = {user.id}
    if user.created_by:
        recipients.add(user.created_by)
    if template.created_by:
        recipients.add(template.created_by)
    if template.user_id:
        recipients.add(template.user_id)
    return {recipient for recipient in recipients if recipient}


def _broadcast_load_event(
    *, load: Load, template: Template, user: User, event_type: str, stage: str
) -> None:
    """Serialize and dispatch a realtime event describing ``load``."""

    recipients = _load_event_recipients(template, user)
    if not recipients:
        return

    event = LoadEvent(
        event_type=event_type,
        stage=stage,
        load=LoadEventLoad(
            id=load.id,
            template_id=load.template_id,
            user_id=load.user_id,
            status=load.status,
            file_name=load.file_name,
            total_rows=load.total_rows,
            error_rows=load.error_rows,
            report_path=load.report_path,
            created_at=load.created_at,
            started_at=load.started_at,
            finished_at=load.finished_at,
        ),
        template=LoadEventTemplateSummary(
            id=template.id,
            user_id=template.user_id,
            name=template.name,
            status=template.status,
            description=template.description,
            table_name=template.table_name,
            created_at=template.created_at,
            updated_at=template.updated_at,
            is_active=template.is_active,
            deleted=template.deleted,
            deleted_by=template.deleted_by,
            deleted_at=template.deleted_at,
        ),
        user=LoadEventUserSummary(
            id=user.id,
            name=user.name,
            email=user.email,
        ),
    )
    dispatch_load_event(event, recipients)


def notify_template_created(session: Session, *, template: Template) -> None:
    """Notify the template creator that the resource is available."""

    target_user_id = template.created_by or template.user_id
    if not target_user_id:
        return

    message = f"Creaste la plantilla '{template.name}'."
    _persist_notification(
        session,
        user_id=target_user_id,
        event_type="template.created",
        title="Plantilla creada",
        message=message,
        payload={"template_id": template.id, "status": template.status},
    )


def notify_template_published(session: Session, *, template: Template) -> None:
    """Inform the user who published the template."""

    target_user_id = template.updated_by or template.created_by or template.user_id
    if not target_user_id:
        return

    message = f"Publicaste la plantilla '{template.name}'."
    _persist_notification(
        session,
        user_id=target_user_id,
        event_type="template.published",
        title="Plantilla publicada",
        message=message,
        payload={"template_id": template.id, "status": template.status},
    )


def _persist_or_update_load_notification(
    session: Session,
    *,
    user: User,
    load: Load,
    template: Template,
    event_type: str,
    title: str,
    message: str,
    status: str,
) -> Notification:
    payload = {
        "template_id": template.id,
        "load_id": load.id,
        "status": status,
        "template_name": template.name,
        "file_name": load.file_name,
    }
    repository = NotificationRepository(session)
    existing = repository.get_latest_by_user_and_load(user_id=user.id, load_id=load.id)
    now = now_in_app_timezone()
    if existing is not None:
        updated = Notification(
            id=existing.id,
            user_id=user.id,
            event_type=event_type,
            title=title,
            message=message,
            payload=payload,
            created_at=now,
            read_at=None,
        )
        saved = repository.update(updated)
        dispatch_notification(saved)
        return saved

    return _persist_notification(
        session,
        user_id=user.id,
        event_type=event_type,
        title=title,
        message=message,
        payload=payload,
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
        f"La carga del archivo '{load.file_name}' para la plantilla "
        f"'{template.name}' está siendo procesada. Estado actual: {LOAD_STATUS_PROCESSING}."
    )
    _persist_or_update_load_notification(
        session,
        user=user,
        load=load,
        template=template,
        event_type="load.processing",
        title="Procesamiento en curso",
        message=message,
        status=LOAD_STATUS_PROCESSING,
    )
    _broadcast_load_event(
        load=load,
        template=template,
        user=user,
        event_type="load.processing",
        stage="processing",
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
    start_date = ensure_app_timezone(access.start_date)
    end_date = ensure_app_timezone(access.end_date)
    payload = {
        "template_id": template.id,
        "access_id": access.id,
        "access_start": start_date.isoformat() if start_date else None,
        "access_end": end_date.isoformat() if end_date else None,
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
    user: User,
) -> None:
    """Inform involved parties about the final validation summary."""

    if not load.user_id:
        return

    status = load.status
    if status == LOAD_STATUS_VALIDATED_SUCCESS:
        event_type = "load.validated.success"
        title = "Validación completada"
        message_detail = (
            "se ha validado correctamente"
            f". Estado final: {LOAD_STATUS_VALIDATED_SUCCESS}."
        )
    elif status == LOAD_STATUS_VALIDATED_WITH_ERRORS:
        event_type = "load.validated.errors"
        title = "Validación con observaciones"
        message_detail = (
            "se ha validado con observaciones"
            f". Estado final: {LOAD_STATUS_VALIDATED_WITH_ERRORS}."
        )
    else:
        return

    message = (
        f"La carga del archivo '{load.file_name}' para la plantilla "
        f"'{template.name}' {message_detail}"
    )
    payload = {
        "template_id": template.id,
        "load_id": load.id,
        "status": status,
    }
    _persist_notification(
        session,
        user_id=load.user_id,
        event_type=event_type,
        title=title,
        message=message,
        payload=payload,
    )

    _broadcast_load_event(
        load=load,
        template=template,
        user=user,
        event_type=event_type,
        stage="completed",
    )

    if status != LOAD_STATUS_VALIDATED_SUCCESS:
        return

    creator_id = user.created_by
    if not creator_id:
        return

    admin = UserRepository(session).get(creator_id)
    if admin is None:
        return

    admin_message = (
        f"La carga del archivo '{load.file_name}' del usuario {user.name} para la plantilla "
        f"'{template.name}' se ha validado correctamente. Estado final: {status}."
    )
    admin_payload = {
        "template_id": template.id,
        "load_id": load.id,
        "status": status,
        "user_id": user.id,
        "user_name": user.name,
        "file_name": load.file_name,
    }
    _persist_notification(
        session,
        user_id=admin.id,
        event_type="load.validated.success.admin",
        title="Carga validada exitosamente",
        message=admin_message,
        payload=admin_payload,
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
        title = "Validación exitosa"
        message = (
            f"La carga del archivo '{load.file_name}' para la plantilla "
            f"'{template.name}' se ha validado correctamente. "
            f"Estado final: {LOAD_STATUS_VALIDATED_SUCCESS}."
        )
    elif status == LOAD_STATUS_VALIDATED_WITH_ERRORS:
        event_type = "load.completed.errors"
        title = "Validación con observaciones"
        message = (
            f"La carga del archivo '{load.file_name}' para la plantilla "
            f"'{template.name}' se ha validado con observaciones. "
            f"Estado final: {LOAD_STATUS_VALIDATED_WITH_ERRORS}."
        )
    elif status == LOAD_STATUS_FAILED:
        event_type = "load.completed.failed"
        title = "Validación fallida"
        message = (
            f"La carga del archivo '{load.file_name}' para la plantilla "
            f"'{template.name}' no se pudo validar. Estado final: {LOAD_STATUS_FAILED}. "
            "Verifica que el archivo corresponda a la plantilla."
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
    _persist_or_update_load_notification(
        session,
        user=user,
        load=load,
        template=template,
        event_type=event_type,
        title=title,
        message=message,
        status=status,
    )
    _broadcast_load_event(
        load=load,
        template=template,
        user=user,
        event_type=event_type,
        stage="completed",
    )


__all__ = [
    "notify_template_created",
    "notify_template_published",
    "notify_template_processing",
    "notify_template_access_granted",
    "notify_load_status_changed",
    "notify_load_validated_success",
]
