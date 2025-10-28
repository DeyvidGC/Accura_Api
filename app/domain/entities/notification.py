"""Domain entity representing a user notification."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Notification:
    """Information message delivered to a specific user."""

    id: int | None
    recipient_id: int
    event_type: str
    title: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    read_at: datetime | None = None


__all__ = ["Notification"]
