"""Domain entity representing a validation rule."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Rule:
    """Core attributes describing a validation rule."""

    id: int | None
    name: str
    rule: dict[str, Any] | list[Any]


__all__ = ["Rule"]
