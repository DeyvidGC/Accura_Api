"""Domain entity representing a template column."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TemplateColumn:
    """Core attributes describing a template column definition."""

    id: int | None
    template_id: int
    rule_id: int | None
    name: str
    description: str | None
    data_type: str
    created_by: int | None
    created_at: datetime | None
    updated_by: int | None
    updated_at: datetime | None
    is_active: bool


__all__ = ["TemplateColumn"]
