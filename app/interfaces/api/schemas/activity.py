"""Pydantic schemas for activity feed endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

try:  # pragma: no cover - compatibility with pydantic v1/v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - fallback for pydantic v1
    ConfigDict = None  # type: ignore[misc]


class RecentActivityRead(BaseModel):
    event_id: str = Field(..., description="Identificador único de la actividad")
    event_type: str = Field(..., description="Tipo de evento reportado")
    summary: str = Field(..., description="Descripción corta de la actividad")
    created_at: datetime = Field(..., description="Momento en el que ocurrió el evento")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Información adicional relacionada al evento",
    )

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


__all__ = ["RecentActivityRead"]
