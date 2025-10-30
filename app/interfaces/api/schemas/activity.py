"""Pydantic schemas for activity feed endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecentActivityRead(BaseModel):
    event_id: str = Field(..., description="Identificador único de la actividad")
    event_type: str = Field(..., description="Tipo de evento reportado")
    summary: str = Field(..., description="Descripción corta de la actividad")
    created_at: datetime = Field(..., description="Momento en el que ocurrió el evento")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Información adicional relacionada al evento",
    )

    class Config:
        orm_mode = True


__all__ = ["RecentActivityRead"]
