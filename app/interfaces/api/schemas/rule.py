"""Schemas for validation rule endpoints."""

from typing import Any

from pydantic import BaseModel, Field

try:  # Pydantic v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - compatibility path for pydantic v1
    ConfigDict = None  # type: ignore[misc]

JSONType = dict[str, Any] | list[Any]


class RuleBase(BaseModel):
    name: str = Field(..., max_length=50)
    rule: JSONType


class RuleCreate(RuleBase):
    """Payload required to create a rule."""


class RuleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    rule: JSONType | None = None

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            extra = "forbid"


class RuleRead(RuleBase):
    id: int

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True
