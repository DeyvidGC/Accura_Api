"""Schemas for template user access management."""

from datetime import date, datetime

from typing import TypeAlias

from pydantic import BaseModel, Field, conlist

try:  # pragma: no cover - compatibility helpers for pydantic v1/v2
    from pydantic import field_validator
except ImportError:  # pragma: no cover - fallback for pydantic v1
    field_validator = None  # type: ignore[assignment]
    from pydantic import validator

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

    @staticmethod
    def _ensure_date(value: date | datetime | None, *, allow_none: bool) -> date | None:
        if value is None:
            if allow_none:
                return None
            raise ValueError("start_date no puede ser nulo")
        if isinstance(value, datetime):
            return value.date()
        return value

    if field_validator is not None:  # pragma: no branch

        @field_validator("start_date", mode="before")  # type: ignore[misc[arg-type]]
        @classmethod
        def _coerce_start_date(
            cls, value: date | datetime | None
        ) -> date:  # pragma: no cover - exercised via pydantic
            coerced = cls._ensure_date(value, allow_none=False)
            assert coerced is not None
            return coerced

        @field_validator("end_date", mode="before")  # type: ignore[misc[arg-type]]
        @classmethod
        def _coerce_end_date(
            cls, value: date | datetime | None
        ) -> date | None:  # pragma: no cover - exercised via pydantic
            return cls._ensure_date(value, allow_none=True)

    else:  # pragma: no cover - compatibility for pydantic v1

        @validator("start_date", pre=True, always=True)
        def _coerce_start_date_v1(
            cls, value: date | datetime | None
        ) -> date:  # type: ignore[override]
            coerced = cls._ensure_date(value, allow_none=False)
            assert coerced is not None
            return coerced

        @validator("end_date", pre=True, always=False)
        def _coerce_end_date_v1(
            cls, value: date | datetime | None
        ) -> date | None:  # type: ignore[override]
            return cls._ensure_date(value, allow_none=True)


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
