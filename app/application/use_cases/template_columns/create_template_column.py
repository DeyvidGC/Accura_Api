"""Use case for creating template columns."""

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


def create_template_column(
    session: Session,
    *,
    template_id: int,
    name: str,
    data_type: str,
    description: str | None = None,
    rule_id: int | None = None,
    created_by: int | None = None,
) -> TemplateColumn:
    """Create a new column inside a template."""

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)

    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    try:
        safe_name = ensure_identifier(name, kind="column")
    except IdentifierError as exc:
        raise ValueError(str(exc)) from exc

    try:
        normalized_type = ensure_data_type(data_type)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    existing_columns = column_repository.list_by_template(template_id)
    if any(col.name.lower() == safe_name.lower() for col in existing_columns):
        raise ValueError("Ya existe una columna con ese nombre en la plantilla")

    now = datetime.utcnow()
    column = TemplateColumn(
        id=None,
        template_id=template_id,
        rule_id=rule_id,
        name=safe_name,
        description=description,
        data_type=normalized_type,
        created_by=created_by,
        created_at=now,
        updated_by=None,
        updated_at=None,
        is_active=True,
    )

    saved_column = column_repository.create(column)

    if template.status == "published":
        updated_template = template_repository.get(template_id)
        try:
            drop_template_table(template.table_name)
            create_template_table(updated_template.table_name, updated_template.columns)
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc

    return saved_column
