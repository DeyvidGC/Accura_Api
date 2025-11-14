"""Domain event broadcast when load processing changes state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class LoadEvent:
    """Details representing a change in a load processing lifecycle."""

    event_type: str
    stage: str
    load_id: int | None
    template_id: int | None
    template_name: str
    user_id: int | None
    user_name: str
    file_name: str
    status: str
    total_rows: int
    error_rows: int
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


__all__ = ["LoadEvent"]
