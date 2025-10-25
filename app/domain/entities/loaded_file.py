"""Domain entity representing a stored report for a load execution."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class LoadedFile:
    """Metadata describing a generated report associated with a load."""

    id: int | None
    load_id: int
    name: str
    path: str
    size_bytes: int
    num_load: int
    created_user_id: int
    created_at: datetime | None


__all__ = ["LoadedFile"]
