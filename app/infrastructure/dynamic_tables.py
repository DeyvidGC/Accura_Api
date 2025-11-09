"""Utilities for creating and removing dynamic database tables."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError
from sqlalchemy.types import JSON

from app.domain.entities import TemplateColumn
from app.infrastructure.database import engine

_json_type = JSONB().with_variant(JSON(), "sqlite")
_identifier_regex = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_IDENTIFIER_LENGTH = 63

_DATA_TYPE_MAP: dict[str, object] = {
    "string": String(255),
    "text": Text(),
    "integer": Integer(),
    "float": Float(),
    "boolean": Boolean(),
    "date": Date(),
    "datetime": DateTime(),
    "json": _json_type,
}


class IdentifierError(ValueError):
    """Raised when an invalid SQL identifier is provided."""


class DataTypeError(ValueError):
    """Raised when an unsupported column data type is provided."""


def ensure_identifier(name: str, *, kind: str) -> str:
    """Validate ``name`` as a SQL identifier and return the normalized value."""

    candidate = name.strip()
    if len(candidate) > _MAX_IDENTIFIER_LENGTH:
        msg = (
            f"{kind.capitalize()} '{name}' exceeds the maximum length of "
            f"{_MAX_IDENTIFIER_LENGTH} characters"
        )
        raise IdentifierError(msg)
    if not _identifier_regex.match(candidate):
        msg = (
            f"{kind.capitalize()} '{name}' must begin with a letter or underscore "
            "and contain only letters, numbers, or underscores"
        )
        raise IdentifierError(msg)
    return candidate.lower()


def normalize_identifier(name: str, *, kind: str) -> str:
    """Return a safe SQL identifier derived from ``name``.

    ``name`` may contain spaces or other separators. This helper removes
    diacritics, normalizes whitespace and punctuation into underscores and
    finally delegates to :func:`ensure_identifier` to validate the result.
    """

    decomposed = unicodedata.normalize("NFD", name or "")
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    collapsed = re.sub(r"[^A-Za-z0-9]+", "_", stripped)
    candidate = collapsed.strip("_")
    if not candidate:
        msg = (
            f"{kind.capitalize()} '{name}' must contain at least one "
            "alphanumeric character"
        )
        raise IdentifierError(msg)
    return ensure_identifier(candidate, kind=kind)


def _column_type_from_string(data_type: str):
    try:
        return _DATA_TYPE_MAP[data_type.lower()]
    except KeyError as exc:
        msg = (
            "Tipo de dato no soportado. Usa uno de: "
            + ", ".join(sorted(_DATA_TYPE_MAP))
        )
        raise DataTypeError(msg) from exc


def ensure_data_type(data_type: str) -> str:
    """Validate that ``data_type`` is supported and return its normalized value."""

    _column_type_from_string(data_type)
    return data_type.lower()


def create_template_table(table_name: str, columns: Sequence[TemplateColumn]) -> None:
    """Create a physical table matching the provided template definition."""

    safe_table_name = ensure_identifier(table_name, kind="table")

    metadata = MetaData()
    table_columns = [Column("id", Integer, primary_key=True, autoincrement=True)]

    for column in columns:
        safe_column_name = normalize_identifier(column.name, kind="column")
        column_type = _column_type_from_string(column.data_type)
        table_columns.append(Column(safe_column_name, column_type))

    table_columns.extend(
        [
            Column("status", String(20), nullable=False, default="Procesado"),
            Column("observaciones", Text(), nullable=True),
            Column("numero_operacion", Integer, nullable=False),
        ]
    )

    table = Table(safe_table_name, metadata, *table_columns)
    try:
        metadata.create_all(bind=engine, tables=[table], checkfirst=True)
    except SQLAlchemyError as exc:  # pragma: no cover - passthrough for db layer
        msg = f"No se pudo crear la tabla temporal '{safe_table_name}': {exc}"
        raise RuntimeError(msg) from exc


def drop_template_table(table_name: str) -> None:
    """Drop the physical table for the provided template if it exists."""

    safe_table_name = ensure_identifier(table_name, kind="table")

    metadata = MetaData()
    try:
        table = Table(safe_table_name, metadata, autoload_with=engine)
    except NoSuchTableError:
        return
    try:
        table.drop(bind=engine, checkfirst=True)
    except SQLAlchemyError as exc:  # pragma: no cover - passthrough for db layer
        msg = f"No se pudo eliminar la tabla temporal '{safe_table_name}': {exc}"
        raise RuntimeError(msg) from exc


__all__ = [
    "IdentifierError",
    "DataTypeError",
    "ensure_data_type",
    "create_template_table",
    "drop_template_table",
    "ensure_identifier",
    "normalize_identifier",
]
