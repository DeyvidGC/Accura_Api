"""Helpers to broadcast realtime events to connected clients."""

from __future__ import annotations

import asyncio
import copy
from typing import Any, Iterable, Set

from anyio import from_thread

from .manager import NotificationConnectionManager, notification_manager


class RealtimeEventPublisher:
    """Dispatch structured realtime events to websocket subscribers."""

    def __init__(self, manager: NotificationConnectionManager) -> None:
        self._manager = manager

    def dispatch(self, user_id: int, *, event_type: str, payload: Any) -> None:
        """Schedule a realtime ``event_type`` event for ``user_id``."""

        if not user_id:
            return

        message = {"type": event_type, "data": copy.deepcopy(payload)}
        self._schedule_send(user_id, message)

    def dispatch_many(
        self,
        user_ids: Iterable[int],
        *,
        event_type: str,
        payload: Any,
    ) -> None:
        """Broadcast an event to multiple ``user_ids``."""

        seen: Set[int] = set()
        for user_id in user_ids:
            if not user_id or user_id in seen:
                continue
            seen.add(user_id)
            self.dispatch(user_id, event_type=event_type, payload=payload)

    def _schedule_send(self, user_id: int, message: dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            if hasattr(from_thread, "start_soon"):
                from_thread.start_soon(self._manager.send_to_user, user_id, message)
            else:  # pragma: no cover - compatibility path for older anyio
                from_thread.run(self._manager.send_to_user, user_id, message)
        else:
            loop.create_task(self._manager.send_to_user(user_id, message))


realtime_event_publisher = RealtimeEventPublisher(notification_manager)


def dispatch_realtime_event(
    user_ids: Iterable[int], *, event_type: str, payload: Any
) -> None:
    """Public helper to broadcast realtime events to ``user_ids``."""

    realtime_event_publisher.dispatch_many(
        user_ids, event_type=event_type, payload=payload
    )


__all__ = [
    "RealtimeEventPublisher",
    "realtime_event_publisher",
    "dispatch_realtime_event",
]

