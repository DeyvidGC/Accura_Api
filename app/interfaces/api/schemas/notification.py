"""Pydantic models describing notification payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NotificationMarkReadRequest(BaseModel):
    """Payload used to mark a batch of notifications as read."""

    ids: list[int] = Field(..., min_length=1, description="Identificadores de notificaciones")

    def unique_ids(self) -> list[int]:
        """Return the list of identifiers without duplicates preserving order."""

        unique: list[int] = []
        seen: set[int] = set()
        for notification_id in self.ids:
            if notification_id in seen:
                continue
            seen.add(notification_id)
            unique.append(notification_id)
        return unique


class NotificationRead(BaseModel):
    """Representation of a notification delivered to the client."""

    id: int
    user_id: int
    event_type: str
    title: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    read_at: datetime | None = None


__all__ = ["NotificationMarkReadRequest", "NotificationRead"]
