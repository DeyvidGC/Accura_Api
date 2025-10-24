"""Use case for updating template columns."""

from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import TemplateColumn
from app.infrastructure.dynamic_tables import (
    IdentifierError,
    ensure_data_type,
    ensure_identifier,
    create_template_table,
    drop_template_table,
)
from app.infrastructure.repositories import (
    TemplateColumnRepository,
    TemplateRepository,
)


def update_template_column(
    session: Session,
    *,
    template_id: int,
    column_id: int,
    name: str | None = None,
    data_type: str | None = None,
    description: str | None = None,
    rule_id: int | None = None,
    is_active: bool | None = None,
    updated_by: int | None = None,
) -> TemplateColumn:
    """Update an existing template column."""

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)

    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

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

    updated_column = replace(
        current,
        name=new_name,
        data_type=new_data_type,
        description=description if description is not None else current.description,
        rule_id=rule_id if rule_id is not None else current.rule_id,
        is_active=is_active if is_active is not None else current.is_active,
        updated_by=updated_by if updated_by is not None else current.updated_by,
        updated_at=datetime.utcnow(),
    )

    saved_column = column_repository.update(updated_column)

    if template.status == "published":
        updated_template = template_repository.get(template_id)
        try:
            drop_template_table(template.table_name)
            create_template_table(updated_template.table_name, updated_template.columns)
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc

    return saved_column
