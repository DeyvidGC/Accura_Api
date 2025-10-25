"""Schemas for template user access management."""

from datetime import datetime

from pydantic import BaseModel, Field

try:  # pragma: no cover - compatibility with pydantic v1/v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - fallback for pydantic v1
    ConfigDict = None  # type: ignore[misc]


class TemplateUserAccessCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    start_date: datetime | None = None
    end_date: datetime | None = None

    if ConfigDict is not None:  # pragma: no branch
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover
        class Config:
            extra = "forbid"


class TemplateUserAccessRead(BaseModel):
    id: int
    template_id: int
    user_id: int
    start_date: datetime
    end_date: datetime | None
    revoked_at: datetime | None
    revoked_by: int | None
    created_at: datetime | None
    updated_at: datetime | None

    if ConfigDict is not None:  # pragma: no branch
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover
        class Config:
            orm_mode = True


__all__ = ["TemplateUserAccessCreate", "TemplateUserAccessRead"]
