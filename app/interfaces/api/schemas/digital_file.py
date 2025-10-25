"""Schemas for digital file endpoints."""

from datetime import datetime

from pydantic import BaseModel

try:  # pragma: no cover - compatibility with pydantic v1/v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - fallback for pydantic v1
    ConfigDict = None  # type: ignore[misc]


class DigitalFileRead(BaseModel):
    id: int
    template_id: int
    name: str
    description: str | None
    path: str
    created_by: int | None
    created_at: datetime | None
    updated_by: int | None
    updated_at: datetime | None

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


__all__ = ["DigitalFileRead"]
