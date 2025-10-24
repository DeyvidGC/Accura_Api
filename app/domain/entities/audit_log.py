"""Domain entity representing an audit entry for template table operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass
class AuditLog:
    """Captured information about template table lifecycle events."""

    id: int | None
    template_name: str
    columns: Sequence[str]
    operation: str
    created_by: int | None
    created_at: datetime | None
    updated_by: int | None
    updated_at: datetime | None


__all__ = ["AuditLog"]
