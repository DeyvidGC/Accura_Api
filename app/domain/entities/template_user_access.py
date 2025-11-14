"""Domain entity representing template access assigned to users."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.utils import ensure_app_timezone, now_in_app_timezone


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
        current = ensure_app_timezone(reference_time) or now_in_app_timezone()
        start = ensure_app_timezone(self.start_date)
        if start is None:
            return False
        if current < start:
            return False
        end = ensure_app_timezone(self.end_date)
        if end is not None and current > end:
            return False
        return True


__all__ = ["TemplateUserAccess"]
