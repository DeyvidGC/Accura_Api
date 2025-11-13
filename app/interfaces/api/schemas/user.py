"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

try:  # Pydantic v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - compatibility path for pydantic v1
    ConfigDict = None  # type: ignore[misc]


class RoleRead(BaseModel):
    id: int
    name: str
    alias: str

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class UserBase(BaseModel):
    name: str = Field(..., max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    role_id: int = Field(..., ge=1)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    is_active: bool | None = None
    role_id: int | None = None

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(extra="forbid")
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            extra = "forbid"


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    must_change_password: bool
    last_login: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    is_active: bool
    deleted: bool
    deleted_by: int | None
    deleted_at: datetime | None
    role: RoleRead

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True


class UserSummaryRead(BaseModel):
    id: int
    name: str
    email: EmailStr

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True
