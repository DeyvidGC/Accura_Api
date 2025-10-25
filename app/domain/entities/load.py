"""Domain entity representing a data load executed by a user."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Load:
    """Metadata describing a data import performed against a template."""

    id: int | None
    template_id: int
    user_id: int
    status: str
    file_name: str
    total_rows: int
    error_rows: int
    report_path: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


__all__ = ["Load"]
