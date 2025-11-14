"""Utilities for creating and removing dynamic database tables."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from sqlalchemy import Column, Date, Float, Integer, MetaData, String, Table, Text
from sqlalchemy.dialects.mssql import JSON as MSSQLJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError
from sqlalchemy.types import JSON

from app.domain.entities import TemplateColumn
from app.infrastructure.database import engine

_json_type = (
    JSONB().with_variant(JSON(), "sqlite").with_variant(MSSQLJSON(), "mssql")
)
_identifier_regex = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_IDENTIFIER_LENGTH = 63


def _normalize_type_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(label))
    ascii_label = "".join(char for char in normalized if not unicodedata.combining(char))
    collapsed = re.sub(r"[\s\-_/]+", " ", ascii_label)
    return collapsed.lower().strip()


_DATA_TYPE_MAP: dict[str, object] = {
    "texto": Text(),
    "numero": Float(),
    "documento": String(255),
    "lista": Text(),
    "lista compleja": _json_type,
    "lista completa": _json_type,
    "telefono": String(50),
    "correo": String(255),
    "fecha": Date(),
    "dependencia": Text(),
    "validacion conjunta": Text(),
    "duplicados": Text(),
}

_CANONICAL_TYPE_LABELS: dict[str, str] = {
    "texto": "Texto",
    "numero": "Número",
    "documento": "Documento",
    "lista": "Lista",
    "lista compleja": "Lista compleja",
    "lista completa": "Lista compleja",
    "telefono": "Telefono",
    "correo": "Correo",
    "fecha": "Fecha",
    "dependencia": "Dependencia",
    "validacion conjunta": "Validación conjunta",
    "duplicados": "Duplicados",
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
    normalized = _normalize_type_label(data_type)
    try:
        return _DATA_TYPE_MAP[normalized]
    except KeyError as exc:
        allowed_labels = {
            _CANONICAL_TYPE_LABELS.get(key, key)
            for key in _DATA_TYPE_MAP.keys()
        }
        msg = (
            "Tipo de dato no soportado. Usa uno de: "
            + ", ".join(sorted(allowed_labels))
        )
        raise DataTypeError(msg) from exc


def ensure_data_type(data_type: str) -> str:
    """Validate that ``data_type`` is supported and return its normalized value."""

    normalized = _normalize_type_label(data_type)
    _column_type_from_string(data_type)
    return _CANONICAL_TYPE_LABELS.get(normalized, normalized)


def create_template_table(table_name: str, columns: Sequence[TemplateColumn]) -> None:
    """Create a physical table matching the provided template definition."""

    safe_table_name = ensure_identifier(table_name, kind="table")

    metadata = MetaData()
    table_columns = [Column("id", Integer, primary_key=True, autoincrement=True)]
    reserved_names = {column.name for column in table_columns}

    for column in columns:
        safe_column_name = normalize_identifier(column.name, kind="column")
        if safe_column_name in reserved_names:
            msg = (
                "No se pudo crear la tabla temporal "
                f"'{safe_table_name}': el nombre de columna "
                f"'{column.name}' genera un identificador duplicado "
                f"'{safe_column_name}'. Usa nombres de columnas únicos."
            )
            raise RuntimeError(msg)
        column_type = _column_type_from_string(column.data_type)
        table_columns.append(Column(safe_column_name, column_type))
        reserved_names.add(safe_column_name)

    extra_columns = [
        Column("status", String(20), nullable=False, default="Procesado"),
        Column("observaciones", Text(), nullable=True),
        Column("numero_operacion", Integer, nullable=False),
    ]

    for column in extra_columns:
        if column.name in reserved_names:
            msg = (
                "No se pudo crear la tabla temporal "
                f"'{safe_table_name}': el nombre de columna reservada "
                f"'{column.name}' entra en conflicto con los nombres del "
                "template. Usa nombres diferentes para evitar duplicados."
            )
            raise RuntimeError(msg)
        reserved_names.add(column.name)

    table_columns.extend(extra_columns)

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
