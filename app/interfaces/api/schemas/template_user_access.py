"""Schemas for template user access management."""

from datetime import date, datetime

from typing import TypeAlias

from pydantic import BaseModel, Field, conlist

try:  # pragma: no cover - compatibility with pydantic v1/v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - fallback for pydantic v1
    ConfigDict = None  # type: ignore[misc]


class TemplateUserAccessRead(BaseModel):
    id: int
    template_id: int
    user_id: int
    start_date: date
    end_date: date | None
    revoked_at: datetime | None
    revoked_by: int | None
    created_at: datetime | None
    updated_at: datetime | None

    if ConfigDict is not None:  # pragma: no branch
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover
        class Config:
            orm_mode = True


class TemplateUserAccessGrantItem(BaseModel):
    template_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)
    start_date: date | None = None
    end_date: date | None = None

    if ConfigDict is not None:  # pragma: no branch
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover
        class Config:
            extra = "forbid"


class TemplateUserAccessRevokeItem(BaseModel):
    template_id: int = Field(..., ge=1)
    access_id: int = Field(..., ge=1)

    if ConfigDict is not None:  # pragma: no branch
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover
        class Config:
            extra = "forbid"


class TemplateUserAccessUpdateItem(BaseModel):
    template_id: int = Field(..., ge=1)
    access_id: int = Field(..., ge=1)
    start_date: date | None = None
    end_date: date | None = None

    if ConfigDict is not None:  # pragma: no branch
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover
        class Config:
            extra = "forbid"

__all__ = [
    "TemplateUserAccessRead",
    "TemplateUserAccessGrantItem",
    "TemplateUserAccessRevokeItem",
    "TemplateUserAccessUpdateItem",
]

try:
    TemplateUserAccessGrantList: TypeAlias = conlist(TemplateUserAccessGrantItem, min_length=1)
    TemplateUserAccessRevokeList: TypeAlias = conlist(TemplateUserAccessRevokeItem, min_length=1)
    TemplateUserAccessUpdateList: TypeAlias = conlist(TemplateUserAccessUpdateItem, min_length=1)
except TypeError:  # pragma: no cover - compatibility with pydantic v1
    TemplateUserAccessGrantList = conlist(TemplateUserAccessGrantItem, min_items=1)
    TemplateUserAccessRevokeList = conlist(TemplateUserAccessRevokeItem, min_items=1)
    TemplateUserAccessUpdateList = conlist(TemplateUserAccessUpdateItem, min_items=1)

__all__ += [
    "TemplateUserAccessGrantList",
    "TemplateUserAccessRevokeList",
    "TemplateUserAccessUpdateList",
]
