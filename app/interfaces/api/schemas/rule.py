"""Schemas for validation rule endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

try:  # Pydantic v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - compatibility path for pydantic v1
    ConfigDict = None  # type: ignore[misc]

JSONType = dict[str, Any] | list[Any]


class RuleBase(BaseModel):
    rule: JSONType


class RuleCreate(RuleBase):
    """Payload required to create a rule."""

    is_active: bool = True


class RuleUpdate(BaseModel):
    rule: JSONType | None = None
    is_active: bool | None = None

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            extra = "forbid"


class RuleRead(RuleBase):
    id: int
    created_by: int | None
    created_at: datetime | None
    updated_by: int | None
    updated_at: datetime | None
    is_active: bool
    deleted: bool
    deleted_by: int | None
    deleted_at: datetime | None

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True
