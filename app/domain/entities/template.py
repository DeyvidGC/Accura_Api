"""Domain entity representing a template."""

from dataclasses import dataclass, field
from datetime import datetime

from .template_column import TemplateColumn


@dataclass
class Template:
    """Core attributes describing a template definition."""

    id: int | None
    user_id: int
    name: str
    status: str
    description: str | None
    table_name: str
    created_by: int | None
    created_at: datetime | None
    updated_by: int | None
    updated_at: datetime | None
    is_active: bool
    columns: list[TemplateColumn] = field(default_factory=list)


__all__ = ["Template"]
