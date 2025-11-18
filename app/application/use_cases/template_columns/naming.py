"""Helpers for normalizing template column names provided by users."""

from __future__ import annotations

import re
import unicodedata

from app.infrastructure.dynamic_tables import normalize_identifier

_TILDE_MARK = "\u0303"


def _contains_forbidden_diacritics(value: str) -> bool:
    normalized = unicodedata.normalize("NFD", value)
    for index, char in enumerate(normalized):
        if not unicodedata.combining(char):
            continue
        if char == _TILDE_MARK and index > 0 and normalized[index - 1].lower() == "n":
            continue
        return True
    return False


def normalize_column_display_name(name: str) -> str:
    """Return ``name`` formatted for storage and display.

    The returned value collapses internal whitespace, converts the full string
    to lowercase except for the first character (which is capitalized) and
    raises a :class:`ValueError` if the input includes tildes or other
    diacritics (excluding the letter "ñ").
    """

    if not isinstance(name, str):
        raise ValueError("El nombre de la columna debe ser texto")

    collapsed = re.sub(r"\s+", " ", name.strip())
    if not collapsed:
        raise ValueError("El nombre de la columna no puede estar vacío")

    if _contains_forbidden_diacritics(collapsed):
        raise ValueError("El nombre de la columna no puede contener tildes")

    lowered = collapsed.lower()
    return lowered[0].upper() + lowered[1:] if lowered else lowered


def derive_column_identifier(display_name: str) -> str:
    """Return the SQL identifier associated with ``display_name``."""

    return normalize_identifier(display_name, kind="column")


__all__ = [
    "derive_column_identifier",
    "normalize_column_display_name",
]
