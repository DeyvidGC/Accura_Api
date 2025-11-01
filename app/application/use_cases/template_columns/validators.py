"""Validation helpers for template column dependencies."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.domain.entities import TemplateColumn
from app.infrastructure.repositories import RuleRepository

_RULE_TYPES_REQUIRING_HEADER_FIELD = {"lista compleja", "dependencia"}
_RULE_TYPES_REQUIRING_COLUMN_HEADER = {"lista compleja"}
_NORMALIZATION_STOPWORDS: set[str] = {
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "uno",
    "y",
    "the",
    "a",
}


@dataclass(frozen=True)
class _ColumnLabel:
    name: str
    normalized: str
    tokens: tuple[str, ...]
    token_set: frozenset[str]


def _normalize_type_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(label))
    ascii_label = "".join(char for char in normalized if not unicodedata.combining(char))
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", ascii_label)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", separated)
    collapsed = re.sub(r"[\s\-_/]+", " ", separated)
    return collapsed.lower().strip()


def _tokenize_label(label: str) -> tuple[str, ...]:
    normalized = _normalize_type_label(label)
    if not normalized:
        return ()
    tokens = [
        token
        for token in normalized.split()
        if token and token not in _NORMALIZATION_STOPWORDS
    ]
    return tuple(tokens)


def _iter_rule_definitions(rule_data: Any) -> list[Mapping[str, Any]]:
    if isinstance(rule_data, Mapping):
        return [rule_data]
    if isinstance(rule_data, list):
        definitions: list[Mapping[str, Any]] = []
        for entry in rule_data:
            definitions.extend(_iter_rule_definitions(entry))
        return definitions
    return []


def _build_available_labels(columns: Sequence[TemplateColumn]) -> list[_ColumnLabel]:
    labels: list[_ColumnLabel] = []
    for column in columns:
        normalized = _normalize_type_label(column.name)
        tokens = _tokenize_label(column.name)
        labels.append(
            _ColumnLabel(
                name=column.name,
                normalized=normalized,
                tokens=tokens,
                token_set=frozenset(tokens),
            )
        )
    return labels


def _resolve_rule_name(definition: Mapping[str, Any], column: TemplateColumn) -> str:
    raw_name = definition.get("Nombre de la regla")
    if isinstance(raw_name, str) and raw_name.strip():
        return raw_name.strip()
    return column.name


def _header_matches(header: str, candidates: Sequence[_ColumnLabel]) -> bool:
    normalized = _normalize_type_label(header)
    tokens = _tokenize_label(header)
    token_set = frozenset(tokens)

    for candidate in candidates:
        if normalized and normalized == candidate.normalized:
            return True
        if tokens and tokens == candidate.tokens:
            return True
        if token_set and candidate.token_set:
            if token_set.issubset(candidate.token_set) or candidate.token_set.issubset(token_set):
                return True
    return False


def normalize_rule_header(header: Sequence[str] | None) -> tuple[str, ...] | None:
    """Normalize user provided headers into a tuple of stripped strings."""

    if header is None:
        return None

    normalized: list[str] = []
    for value in header:
        if not isinstance(value, str):
            raise ValueError("Los headers de las reglas deben ser texto.")
        stripped = value.strip()
        if stripped:
            normalized.append(stripped)

    if not normalized:
        return None

    return tuple(normalized)


def ensure_rule_header_dependencies(
    *,
    columns: Sequence[TemplateColumn],
    rule_repository: RuleRepository,
) -> None:
    """Ensure complex list and dependency rules reference available headers."""

    active_columns = [column for column in columns if column.is_active]
    if not active_columns:
        return

    labels = _build_available_labels(active_columns)
    rule_cache: dict[int, Any] = {}

    for column in active_columns:
        column_headers = normalize_rule_header(column.rule_header)
        header_values = list(column_headers) if column_headers else []

        if column.rule_id is None:
            if header_values:
                raise ValueError(
                    f"La columna '{column.name}' no puede definir headers sin una regla asociada."
                )
            continue

        cached = rule_cache.get(column.rule_id)
        if cached is None:
            fetched = rule_repository.get(column.rule_id)
            if fetched is None or not fetched.is_active:
                raise ValueError(
                    f"La regla asociada a la columna '{column.name}' no está disponible."
                )
            rule_cache[column.rule_id] = fetched
            rule_payload = fetched.rule
        else:
            rule_payload = cached.rule

        definitions = _iter_rule_definitions(rule_payload)
        allows_column_header = False
        requires_column_header = False
        for definition in definitions:
            rule_type = _normalize_type_label(definition.get("Tipo de dato", ""))
            if rule_type not in _RULE_TYPES_REQUIRING_HEADER_FIELD:
                continue

            if rule_type in _RULE_TYPES_REQUIRING_COLUMN_HEADER:
                allows_column_header = True
                requires_column_header = True

            headers = definition.get("Header")
            if not isinstance(headers, list):
                raise ValueError(
                    f"La regla '{_resolve_rule_name(definition, column)}' debe incluir un header con los campos relacionados."
                )

            valid_headers = [
                header.strip()
                for header in headers
                if isinstance(header, str) and header.strip()
            ]
            if not valid_headers:
                raise ValueError(
                    f"La regla '{_resolve_rule_name(definition, column)}' debe definir encabezados válidos."
                )

            missing = [
                header
                for header in valid_headers
                if not _header_matches(header, labels)
            ]
            if missing:
                missing_str = ", ".join(sorted(set(missing)))
                raise ValueError(
                    f"La regla '{_resolve_rule_name(definition, column)}' requiere que la plantilla incluya las columnas {missing_str}."
                )

        if header_values and not allows_column_header:
            raise ValueError(
                f"La columna '{column.name}' no admite headers para la regla seleccionada."
            )

        if requires_column_header and not header_values:
            raise ValueError(
                f"La columna '{column.name}' debe definir headers para la regla asignada."
            )

        if header_values:
            missing_headers = [
                header
                for header in header_values
                if not _header_matches(header, labels)
            ]
            if missing_headers:
                missing_str = ", ".join(sorted(set(missing_headers)))
                raise ValueError(
                    f"Los headers configurados para la columna '{column.name}' requieren que la plantilla incluya las columnas {missing_str}."
                )


__all__ = ["ensure_rule_header_dependencies", "normalize_rule_header"]
