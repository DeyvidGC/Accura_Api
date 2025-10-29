"""Utility helpers to push notifications to websocket subscribers."""

from __future__ import annotations

import asyncio
from typing import Any

from anyio import from_thread

from app.domain.entities import Notification

from .manager import NotificationConnectionManager, notification_manager


class NotificationPublisher:
    """Serialize notifications and schedule their delivery."""

    def __init__(self, manager: NotificationConnectionManager) -> None:
        self._manager = manager

    def dispatch(self, notification: Notification) -> None:
        """Schedule ``notification`` to be delivered to its user."""

        message = {"type": "notification", "data": self._serialize(notification)}
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            if hasattr(from_thread, "start_soon"):
                from_thread.start_soon(
                    self._manager.send_to_user, notification.user_id, message
                )
            else:
                from_thread.run(
                    self._manager.send_to_user, notification.user_id, message
                )
        else:
            loop.create_task(
                self._manager.send_to_user(notification.user_id, message)
            )

    @staticmethod
    def _serialize(notification: Notification) -> dict[str, Any]:
        return {
            "id": notification.id,
            "user_id": notification.user_id,
            "event_type": notification.event_type,
            "title": notification.title,
            "message": notification.message,
            "payload": notification.payload or {},
            "created_at": notification.created_at.isoformat()
            if notification.created_at
            else None,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
        }


notification_publisher = NotificationPublisher(notification_manager)


def dispatch_notification(notification: Notification) -> None:
    """Public helper that delegates to the shared publisher instance."""

    notification_publisher.dispatch(notification)


def serialize_notification(notification: Notification) -> dict[str, Any]:
    """Return the websocket payload representation for ``notification``."""

    return NotificationPublisher._serialize(notification)


__all__ = [
    "NotificationPublisher",
    "notification_publisher",
    "dispatch_notification",
    "serialize_notification",
]
