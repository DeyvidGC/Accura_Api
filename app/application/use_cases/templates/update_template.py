"""Use case for updating templates."""

from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import AuditLog, Template
from app.infrastructure.dynamic_tables import (
    IdentifierError,
    create_template_table,
    drop_template_table,
    ensure_identifier,
)
from app.infrastructure.repositories import AuditLogRepository, TemplateRepository

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
    """Update a template and manage its dynamic table lifecycle.

    Raises:
        ValueError: If the template does not exist or if immutable fields are modified
            while the template is published.
    """

    repository = TemplateRepository(session)
    current = repository.get(template_id)
    if current is None:
        raise ValueError("Plantilla no encontrada")

    if current.status == "published":
        invalid_updates: dict[str, object | None] = {
            "name": name,
            "description": description,
            "table_name": table_name,
            "is_active": is_active,
        }
        attempted_changes = [
            field
            for field, value in invalid_updates.items()
            if value is not None and value != getattr(current, field)
        ]
        if attempted_changes:
            raise ValueError(
                "Solo se puede cambiar el estado de una plantilla publicada"
            )

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

    audit_repository = AuditLogRepository(session)

    status_changed = current.status != saved_template.status
    table_changed = current.table_name != saved_template.table_name

    try:
        drop_performed = False
        if current.status == "published" and (status_changed or table_changed):
            drop_template_table(current.table_name)
            drop_performed = True
            audit_repository.create(
                AuditLog(
                    id=None,
                    template_name=current.name,
                    columns=[column.name for column in current.columns],
                    operation="eliminacion",
                    created_by=updated_template.updated_by,
                    created_at=datetime.utcnow(),
                    updated_by=None,
                    updated_at=None,
                )
            )

        if saved_template.status == "published" and (status_changed or table_changed):
            create_template_table(saved_template.table_name, saved_template.columns)
            operation = "insercion"
            if drop_performed and table_changed:
                operation = "actualizacion"
            audit_repository.create(
                AuditLog(
                    id=None,
                    template_name=saved_template.name,
                    columns=[column.name for column in saved_template.columns],
                    operation=operation,
                    created_by=updated_template.updated_by,
                    created_at=datetime.utcnow(),
                    updated_by=None,
                    updated_at=None,
                )
            )
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

    return saved_template
