"""Schemas exposed by the load management endpoints."""

from datetime import datetime

from pydantic import BaseModel

try:  # Pydantic v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - compatibility path for pydantic v1
    ConfigDict = None  # type: ignore[misc]


class LoadRead(BaseModel):
    id: int
    template_id: int
    user_id: int
    status: str
    file_name: str
    total_rows: int
    error_rows: int
    report_path: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class LoadUploadResponse(BaseModel):
    message: str
    load: LoadRead


__all__ = ["LoadRead", "LoadUploadResponse"]
