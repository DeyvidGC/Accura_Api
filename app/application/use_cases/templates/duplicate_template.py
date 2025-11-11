"""Use case to duplicate an existing template."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.application.use_cases.template_columns.validators import (
    ensure_rule_header_dependencies,
)
from app.application.use_cases.templates.create_template import create_template
from app.domain.entities import Template, TemplateColumn
from app.infrastructure.repositories import (
    RuleRepository,
    TemplateColumnRepository,
    TemplateRepository,
)


def duplicate_template(
    session: Session,
    *,
    template_id: int,
    name: str,
    table_name: str,
    description: str,
    created_by: int | None = None,
) -> Template:
    """Duplicate ``template_id`` using the provided metadata for the new template."""

    template_repository = TemplateRepository(session)
    source_template = template_repository.get(template_id)
    if source_template is None:
        raise ValueError("Plantilla no encontrada")

    duplicated_template = create_template(
        session,
        user_id=source_template.user_id,
        name=name,
        table_name=table_name,
        description=description,
        created_by=created_by,
    )

    if not source_template.columns:
        return duplicated_template

    rule_repository = RuleRepository(session)
    column_repository = TemplateColumnRepository(session)
    now = datetime.utcnow()
    new_columns: list[TemplateColumn] = []
    for column in source_template.columns:
        new_columns.append(
            TemplateColumn(
                id=None,
                template_id=duplicated_template.id,
                rule_ids=column.rule_ids,
                rule_header=column.rule_header,
                name=column.name,
                description=column.description,
                data_type=column.data_type,
                created_by=created_by,
                created_at=now,
                updated_by=None,
                updated_at=None,
                is_active=column.is_active,
                deleted=False,
                deleted_by=None,
                deleted_at=None,
            )
        )

    ensure_rule_header_dependencies(
        columns=new_columns,
        rule_repository=rule_repository,
    )

    column_repository.create_many(new_columns)

    # Refresh the duplicated template so it includes the cloned columns.
    return template_repository.get(duplicated_template.id)


__all__ = ["duplicate_template"]
