"""Aggregate application use cases."""

from .create_greeting import create_greeting
from .users import (
    authenticate_user,
    create_user,
    deactivate_user,
    get_user,
    list_users,
    record_login,
    update_user,
)

__all__ = [
    "authenticate_user",
    "create_greeting",
    "create_user",
    "deactivate_user",
    "get_user",
    "list_users",
    "record_login",
    "update_user",
]
