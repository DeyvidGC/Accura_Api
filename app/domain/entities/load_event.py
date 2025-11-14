"""Domain event broadcast when load processing changes state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class LoadEventLoad:
    """Subset of load attributes broadcast to realtime listeners."""

    id: int | None
    template_id: int | None
    user_id: int | None
    status: str
    file_name: str
    total_rows: int
    error_rows: int
    report_path: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


@dataclass
class LoadEventTemplateSummary:
    """Template details accompanying a realtime load event."""

    id: int | None
    user_id: int | None
    name: str
    status: str
    description: str | None
    table_name: str
    created_at: datetime | None
    updated_at: datetime | None
    is_active: bool
    deleted: bool
    deleted_by: int | None
    deleted_at: datetime | None


@dataclass
class LoadEventUserSummary:
    """User summary attached to load lifecycle events."""

    id: int | None
    name: str
    email: str


@dataclass
class LoadEvent:
    """Details representing a change in a load processing lifecycle."""

    event_type: str
    stage: str
    load: LoadEventLoad
    template: LoadEventTemplateSummary
    user: LoadEventUserSummary


__all__ = [
    "LoadEvent",
    "LoadEventLoad",
    "LoadEventTemplateSummary",
    "LoadEventUserSummary",
]
