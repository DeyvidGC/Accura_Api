"""Pydantic models describing notification payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NotificationRead(BaseModel):
    """Representation of a notification delivered to the client."""

    id: int
    recipient_id: int
    event_type: str
    title: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    read_at: datetime | None = None


__all__ = ["NotificationRead"]
