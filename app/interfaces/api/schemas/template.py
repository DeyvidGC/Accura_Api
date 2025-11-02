"""Schemas for template and template column endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

try:  # pragma: no cover - compatibility with pydantic v1/v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - fallback for pydantic v1
    ConfigDict = None  # type: ignore[misc]

TemplateStatus = Literal["unpublished", "published"]


class TemplateColumnBase(BaseModel):
    name: str = Field(..., max_length=50)
    data_type: str = Field(..., max_length=50)
    description: str | None = Field(default=None, max_length=255)
    rule_id: int | None = Field(default=None, ge=1)
    header: list[str] | None = Field(default=None)


class TemplateColumnCreate(TemplateColumnBase):
    """Payload required to create a template column."""


class TemplateColumnBulkCreate(BaseModel):
    """Payload wrapper to create many columns at once."""

    columns: list[TemplateColumnCreate]


class TemplateColumnUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    data_type: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    rule_id: int | None = Field(default=None, ge=1)
    header: list[str] | None = None
    is_active: bool | None = None

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            extra = "forbid"


class TemplateColumnRead(TemplateColumnBase):
    id: int
    template_id: int
    created_at: datetime | None
    updated_at: datetime | None
    is_active: bool

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class TemplateBase(BaseModel):
    name: str = Field(..., max_length=50)
    table_name: str = Field(..., max_length=63)
    description: str | None = Field(default=None, max_length=255)


class TemplateCreate(TemplateBase):
    """Payload required to create a template."""


class TemplateDuplicate(BaseModel):
    """Payload required to duplicate an existing template."""

    name: str = Field(..., max_length=50)
    table_name: str = Field(..., max_length=63)
    description: str = Field(..., max_length=255)


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    status: TemplateStatus | None = None
    table_name: str | None = Field(default=None, max_length=63)
    is_active: bool | None = None

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            extra = "forbid"


class TemplateStatusUpdate(BaseModel):
    status: TemplateStatus

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            extra = "forbid"


class TemplateRead(BaseModel):
    id: int
    user_id: int
    name: str
    status: TemplateStatus
    description: str | None
    table_name: str
    created_at: datetime | None
    updated_at: datetime | None
    is_active: bool
    columns: list[TemplateColumnRead]

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True
