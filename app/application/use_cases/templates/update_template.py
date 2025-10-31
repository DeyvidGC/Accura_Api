"""Use case for updating templates."""

from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import AuditLog, DigitalFile, Template
from app.application.use_cases.notifications import notify_template_published
from app.infrastructure.dynamic_tables import (
    IdentifierError,
    create_template_table,
    drop_template_table,
    ensure_identifier,
)
from app.infrastructure.template_files import (
    create_template_excel,
    delete_template_excel,
    relative_to_project_root,
)
from app.application.use_cases.template_columns.validators import (
    ensure_rule_header_dependencies,
)
from app.infrastructure.repositories import (
    AuditLogRepository,
    DigitalFileRepository,
    RuleRepository,
    TemplateRepository,
)

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
    rule_repository = RuleRepository(session)
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
                "Solo se puede cambiar el estado de una plantilla no publicada"
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

    if new_status == "published" and current.status != "published":
        ensure_rule_header_dependencies(
            columns=current.columns,
            rule_repository=rule_repository,
        )

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
    digital_file_repository = DigitalFileRepository(session)

    status_changed = current.status != saved_template.status
    table_changed = current.table_name != saved_template.table_name

    try:
        drop_performed = False
        cleanup_required = False
        if current.status == "published" and (status_changed or table_changed):
            drop_template_table(current.table_name)
            drop_performed = True
            cleanup_required = True
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

        if saved_template.status != "published":
            cleanup_required = True

        if cleanup_required:
            delete_template_excel(current.id, current.name)
            if saved_template.name != current.name:
                delete_template_excel(saved_template.id, saved_template.name)
            digital_file_repository.delete_by_template_id(current.id)

        if saved_template.status == "published" and (status_changed or table_changed):
            create_template_table(saved_template.table_name, saved_template.columns)
            excel_path = create_template_excel(
                saved_template.id,
                saved_template.name,
                saved_template.columns,
            )
            relative_path = relative_to_project_root(excel_path)
            digital_file = digital_file_repository.get_by_template_id(saved_template.id)
            description = saved_template.description
            now = datetime.utcnow()
            if digital_file is None:
                digital_file_repository.create(
                    DigitalFile(
                        id=None,
                        template_id=saved_template.id,
                        name=excel_path.name,
                        description=description,
                        path=relative_path,
                        created_by=updated_template.updated_by,
                        created_at=now,
                        updated_by=None,
                        updated_at=None,
                    )
                )
            else:
                updated_digital_file = replace(
                    digital_file,
                    name=excel_path.name,
                    description=description,
                    path=relative_path,
                    updated_by=updated_template.updated_by,
                    updated_at=now,
                )
                digital_file_repository.update(updated_digital_file)
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

    if status_changed and saved_template.status == "published":
        notify_template_published(session, template=saved_template)

    return saved_template
