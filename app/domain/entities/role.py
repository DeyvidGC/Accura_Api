"""Domain entity representing a user role."""

from dataclasses import dataclass


@dataclass
class Role:
    """Core attributes describing a role that can be assigned to a user."""

    id: int
    name: str
    alias: str


__all__ = ["Role"]
