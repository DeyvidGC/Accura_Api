"""Domain entity representing a user."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    """Core attributes describing an application user."""

    id: int | None
    name: str
    alias: str | None
    email: str
    password: str
    must_change_password: bool
    last_login: datetime | None
    created_by: int | None
    created_at: datetime | None
    updated_by: int | None
    updated_at: datetime | None
    is_active: bool
