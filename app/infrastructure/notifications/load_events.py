"""Helpers to dispatch realtime load events through websocket connections."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Iterable

from anyio import from_thread

from app.domain.entities import LoadEvent

from .manager import NotificationConnectionManager, notification_manager


class LoadEventPublisher:
    """Serialize :class:`LoadEvent` instances and deliver them to listeners."""

    def __init__(self, manager: NotificationConnectionManager) -> None:
        self._manager = manager

    def dispatch(self, event: LoadEvent, recipients: Iterable[int | None]) -> None:
        """Schedule ``event`` to be delivered to the provided ``recipients``."""

        user_ids = {user_id for user_id in recipients if user_id}
        if not user_ids:
            return

        payload = {
            "type": "load-event",
            "data": serialize_load_event(event),
        }

        for user_id in user_ids:
            self._schedule_delivery(user_id, payload)

    def _schedule_delivery(self, user_id: int, message: dict[str, object]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            if hasattr(from_thread, "start_soon"):
                from_thread.start_soon(self._manager.send_to_user, user_id, message.copy())
            else:  # pragma: no cover - compatibility path for anyio<4
                from_thread.run(self._manager.send_to_user, user_id, message.copy())
        else:
            loop.create_task(self._manager.send_to_user(user_id, message.copy()))


def serialize_load_event(event: LoadEvent) -> dict[str, object]:
    """Return a JSON-serializable representation of ``event``."""

    payload = asdict(event)
    for key in ("created_at", "started_at", "finished_at"):
        value = payload.get(key)
        if value is None:
            continue
        payload[key] = value.isoformat()
    return payload


load_event_publisher = LoadEventPublisher(notification_manager)


def dispatch_load_event(event: LoadEvent, recipients: Iterable[int | None]) -> None:
    """Public helper that delegates to :class:`LoadEventPublisher`."""

    load_event_publisher.dispatch(event, recipients)


__all__ = [
    "LoadEventPublisher",
    "load_event_publisher",
    "dispatch_load_event",
    "serialize_load_event",
]
