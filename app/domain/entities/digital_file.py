"""Domain entity describing a stored digital file."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DigitalFile:
    """Metadata for a generated digital file associated with a template."""

    id: int | None
    template_id: int
    name: str
    description: str | None
    path: str
    created_by: int | None
    created_at: datetime | None
    updated_by: int | None
    updated_at: datetime | None


__all__ = ["DigitalFile"]
