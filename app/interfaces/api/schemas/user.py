"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

try:  # Pydantic v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - compatibility path for pydantic v1
    ConfigDict = None  # type: ignore[misc]


class UserBase(BaseModel):
    name: str = Field(..., max_length=50)
    alias: str | None = Field(default=None, max_length=50)
    email: EmailStr
    must_change_password: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    alias: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    must_change_password: bool | None = None


class UserRead(BaseModel):
    id: int
    name: str
    alias: str | None
    email: EmailStr
    must_change_password: bool
    last_login: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    is_active: bool

    if ConfigDict is not None:  # pragma: no branch - runtime configuration
        model_config = ConfigDict(from_attributes=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        class Config:
            orm_mode = True
