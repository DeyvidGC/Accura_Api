"""Use case for updating template columns."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import TemplateColumn
from app.infrastructure.dynamic_tables import (
    IdentifierError,
    ensure_data_type,
    ensure_identifier,
)
from app.infrastructure.repositories import (
    RuleRepository,
    TemplateColumnRepository,
    TemplateRepository,
)

from .validators import ensure_rule_header_dependencies, normalize_rule_header


def update_template_column(
    session: Session,
    *,
    template_id: int,
    column_id: int,
    name: str | None = None,
    data_type: str | None = None,
    description: str | None = None,
    rule_id: int | None = None,
    header: Sequence[str] | None = None,
    header_provided: bool = False,
    is_active: bool | None = None,
    updated_by: int | None = None,
) -> TemplateColumn:
    """Update an existing template column.

    Raises:
        ValueError: If the template does not exist, is published or the column is missing.
    """

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)
    rule_repository = RuleRepository(session)

    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    if template.status == "published":
        raise ValueError("No se pueden modificar las columnas de una plantilla publicada")

    current = column_repository.get(column_id)
    if current is None or current.template_id != template_id:
        raise ValueError("Columna no encontrada")

    new_name = current.name
    if name is not None and name != current.name:
        try:
            safe_name = ensure_identifier(name, kind="column")
        except IdentifierError as exc:
            raise ValueError(str(exc)) from exc

        existing_columns = column_repository.list_by_template(template_id)
        if any(
            col.id != current.id and col.name.lower() == safe_name.lower()
            for col in existing_columns
        ):
            raise ValueError("Ya existe una columna con ese nombre en la plantilla")
        new_name = safe_name

    new_data_type = current.data_type
    if data_type is not None:
        try:
            new_data_type = ensure_data_type(data_type)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    new_header = current.rule_header
    if header_provided:
        new_header = normalize_rule_header(header)

    updated_column = replace(
        current,
        name=new_name,
        data_type=new_data_type,
        description=description if description is not None else current.description,
        rule_id=rule_id if rule_id is not None else current.rule_id,
        rule_header=new_header,
        is_active=is_active if is_active is not None else current.is_active,
        updated_by=updated_by if updated_by is not None else current.updated_by,
        updated_at=datetime.utcnow(),
    )

    existing_columns = list(column_repository.list_by_template(template_id))
    updated_columns = [
        updated_column if col.id == updated_column.id else col for col in existing_columns
    ]

    ensure_rule_header_dependencies(
        columns=updated_columns,
        rule_repository=rule_repository,
    )

    return column_repository.update(updated_column)
