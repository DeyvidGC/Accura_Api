"""Use case for updating templates."""

from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import Template
from app.infrastructure.dynamic_tables import (
    IdentifierError,
    create_template_table,
    drop_template_table,
    ensure_identifier,
)
from app.infrastructure.repositories import TemplateRepository

ALLOWED_STATUSES = {"unpublished", "published"}


def update_template(
    session: Session,
    *,
    template_id: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    table_name: str | None = None,
    is_active: bool | None = None,
    updated_by: int | None = None,
) -> Template:
    """Update a template and manage its dynamic table lifecycle."""

    repository = TemplateRepository(session)
    current = repository.get(template_id)
    if current is None:
        raise ValueError("Plantilla no encontrada")

    new_table_name = current.table_name
    if table_name is not None and table_name != current.table_name:
        try:
            safe_table_name = ensure_identifier(table_name, kind="table")
        except IdentifierError as exc:
            raise ValueError(str(exc)) from exc

        existing = repository.get_by_table_name(safe_table_name)
        if existing is not None and existing.id != template_id:
            raise ValueError("El nombre de la tabla ya está en uso")
        new_table_name = safe_table_name

    new_status = current.status
    if status is not None:
        if status not in ALLOWED_STATUSES:
            raise ValueError("Estado de plantilla no válido")
        new_status = status

    updated_template = replace(
        current,
        name=name if name is not None else current.name,
        description=description if description is not None else current.description,
        status=new_status,
        table_name=new_table_name,
        is_active=is_active if is_active is not None else current.is_active,
        updated_by=updated_by if updated_by is not None else current.updated_by,
        updated_at=datetime.utcnow(),
    )

    saved_template = repository.update(updated_template)

    status_changed = current.status != saved_template.status
    table_changed = current.table_name != saved_template.table_name

    try:
        if current.status == "published" and (status_changed or table_changed):
            drop_template_table(current.table_name)

        if saved_template.status == "published" and (status_changed or table_changed):
            create_template_table(saved_template.table_name, saved_template.columns)
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

    return saved_template
