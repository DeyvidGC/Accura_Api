"""Domain entity representing template access assigned to users."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TemplateUserAccess:
    """Access assignment allowing a user to use a template."""

    id: int | None
    template_id: int
    user_id: int
    start_date: datetime
    end_date: datetime | None
    revoked_at: datetime | None
    revoked_by: int | None
    created_at: datetime | None
    updated_at: datetime | None

    def is_active(self, *, reference_time: datetime | None = None) -> bool:
        """Return ``True`` when the access is active at ``reference_time``."""

        if self.revoked_at is not None:
            return False
        if reference_time is None:
            reference_time = datetime.utcnow()
        if reference_time < self.start_date:
            return False
        if self.end_date is not None and reference_time > self.end_date:
            return False
        return True


__all__ = ["TemplateUserAccess"]
