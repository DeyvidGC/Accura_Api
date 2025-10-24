"""Use case for deleting templates."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import AuditLog
from app.infrastructure.dynamic_tables import drop_template_table
from app.infrastructure.repositories import AuditLogRepository, TemplateRepository


def delete_template(
    session: Session, template_id: int, *, deleted_by: int | None = None
) -> None:
    """Delete the template and its dynamic table if necessary."""

    repository = TemplateRepository(session)
    template = repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    repository.delete(template_id)

    if template.status == "published":
        try:
            drop_template_table(template.table_name)
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc

        audit_repository = AuditLogRepository(session)
        audit_repository.create(
            AuditLog(
                id=None,
                template_name=template.name,
                columns=[column.name for column in template.columns],
                operation="eliminacion",
                created_by=deleted_by,
                created_at=datetime.utcnow(),
                updated_by=None,
                updated_at=None,
            )
        )
