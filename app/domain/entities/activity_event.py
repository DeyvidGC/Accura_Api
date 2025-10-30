"""Domain entity describing an item of recent activity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ActivityEvent:
    """Represents a high level event visible in the activity feed."""

    event_id: str
    event_type: str
    summary: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = ["ActivityEvent"]
