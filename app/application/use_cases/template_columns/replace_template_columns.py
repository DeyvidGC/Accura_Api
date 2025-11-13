"""Use case for replacing all template columns with new definitions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import TemplateColumn
from app.infrastructure.dynamic_tables import IdentifierError
from app.infrastructure.repositories import (
    RuleRepository,
    TemplateColumnRepository,
    TemplateRepository,
)

from .create_template_column import (
    NewTemplateColumnRuleData,
    _prepare_rule_assignments,
)
from .naming import derive_column_identifier, normalize_column_display_name
from .validators import ensure_rule_header_dependencies


@dataclass(frozen=True)
class TemplateColumnReplacementData:
    """Payload describing how to recreate an existing template column."""

    id: int
    name: str | None = None
    description: str | None = None
    rules: Sequence[NewTemplateColumnRuleData] | None = None
    rules_provided: bool = False
    is_active: bool | None = None


def replace_template_columns(
    session: Session,
    *,
    template_id: int,
    updates: Sequence[TemplateColumnReplacementData],
    actor_id: int | None = None,
) -> list[TemplateColumn]:
    """Replace all columns of a template with the provided definitions."""

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)
    rule_repository = RuleRepository(session)

    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    if template.status == "published":
        raise ValueError("No se pueden modificar las columnas de una plantilla publicada")

    existing_columns = list(column_repository.list_by_template(template_id))
    existing_by_id = {column.id: column for column in existing_columns}

    now = datetime.utcnow()
    forbidden_names: set[str] = set()
    forbidden_identifiers: set[str] = set()

    new_columns: list[TemplateColumn] = []

    for update in updates:
        current = existing_by_id.get(update.id)
        if current is None:
            raise ValueError("Columna no encontrada")

        if update.name is None:
            normalized_name = current.name
        else:
            normalized_name = normalize_column_display_name(update.name)

        try:
            identifier = derive_column_identifier(normalized_name)
        except IdentifierError as exc:
            raise ValueError(str(exc)) from exc

        normalized_key = normalized_name.lower()
        if normalized_key in forbidden_names or identifier in forbidden_identifiers:
            raise ValueError("Ya existe una columna con ese nombre en la plantilla")

        forbidden_names.add(normalized_key)
        forbidden_identifiers.add(identifier)

        if update.rules_provided:
            assignments, normalized_type = _prepare_rule_assignments(
                rule_repository, update.rules
            )
        else:
            assignments = tuple(current.rules)
            normalized_type = current.data_type

        created_by = current.created_by if current.created_by is not None else actor_id
        created_at = current.created_at if current.created_at is not None else now

        new_columns.append(
            TemplateColumn(
                id=None,
                template_id=template_id,
                rules=assignments,
                name=normalized_name,
                description=(
                    update.description
                    if update.description is not None
                    else current.description
                ),
                data_type=normalized_type,
                created_by=created_by,
                created_at=created_at,
                updated_by=None,
                updated_at=None,
                is_active=(
                    current.is_active if update.is_active is None else update.is_active
                ),
                deleted=False,
                deleted_by=None,
                deleted_at=None,
            )
        )

    ensure_rule_header_dependencies(
        columns=new_columns,
        rule_repository=rule_repository,
    )

    for column in existing_columns:
        column_repository.delete(column.id, deleted_by=actor_id)

    if not new_columns:
        return []

    return column_repository.create_many(new_columns)


__all__ = [
    "TemplateColumnReplacementData",
    "replace_template_columns",
]
