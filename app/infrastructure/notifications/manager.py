"""Connection management helpers for notification websockets."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, DefaultDict, Set

from fastapi import WebSocket


class NotificationConnectionManager:
    """Manage active websocket connections grouped by user."""

    def __init__(self) -> None:
        self._connections: DefaultDict[int, Set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Accept the websocket connection and register it for ``user_id``."""

        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        """Remove ``websocket`` from the pool for ``user_id``."""

        connections = self._connections.get(user_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict[str, Any]) -> None:
        """Send ``message`` to every active connection for ``user_id``."""

        connections = list(self._connections.get(user_id, set()))
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:  # pragma: no cover - defensive cleanup
                self.disconnect(user_id, connection)


notification_manager = NotificationConnectionManager()


__all__ = ["NotificationConnectionManager", "notification_manager"]
