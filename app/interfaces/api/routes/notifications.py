"""Endpoints and websocket handler for realtime notifications."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.domain.entities import Notification, User
from app.infrastructure.database import SessionLocal, get_db
from app.infrastructure.notifications import notification_manager, serialize_notification
from app.infrastructure.repositories import NotificationRepository
from app.interfaces.api.dependencies import get_current_active_user, get_current_user
from app.interfaces.api.schemas import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _notification_to_schema(notification: Notification) -> NotificationRead:
    return NotificationRead(
        id=notification.id or 0,
        user_id=notification.user_id,
        event_type=notification.event_type,
        title=notification.title,
        message=notification.message,
        payload=notification.payload or {},
        created_at=notification.created_at,
        read_at=notification.read_at,
    )


def _notification_to_payload(notification: Notification) -> dict[str, Any]:
    return serialize_notification(notification)


@router.get("/", response_model=list[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[NotificationRead]:
    """Return the most recent notifications for the authenticated user."""

    notifications = NotificationRepository(db).list_for_user(
        current_user.id,
        include_created_users=current_user.is_admin(),
    )
    return [_notification_to_schema(notification) for notification in notifications]


@router.websocket("/ws")
async def notifications_websocket(websocket: WebSocket) -> None:
    """Websocket endpoint that streams notifications to the authenticated user."""

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    session = SessionLocal()
    try:
        user = get_current_user(token=token, db=session)
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario inactivo")
        pending_notifications = NotificationRepository(session).list_unread_for_user(
            user.id
        )
    except HTTPException:
        await websocket.close(code=1008)
        session.close()
        return
    except Exception:  # pragma: no cover - defensive path
        await websocket.close(code=1011)
        session.close()
        return
    finally:
        session.close()

    await notification_manager.connect(user.id, websocket)
    try:
        if pending_notifications:
            await websocket.send_json(
                {"type": "init", "data": [_notification_to_payload(n) for n in pending_notifications]}
            )
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception:
                continue

            if not isinstance(message, dict):
                continue

            message_type = message.get("type")
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if message_type == "ack":
                ids = message.get("ids", [])
                if isinstance(ids, list) and ids:
                    ack_session = SessionLocal()
                    try:
                        NotificationRepository(ack_session).mark_as_read(ids, user_id=user.id)
                    finally:
                        ack_session.close()
                continue
    except WebSocketDisconnect:
        notification_manager.disconnect(user.id, websocket)
    except Exception:  # pragma: no cover - defensive path
        notification_manager.disconnect(user.id, websocket)
        raise
