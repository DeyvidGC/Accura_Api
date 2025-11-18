"""Utilities for regenerating artifacts after template column changes."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.entities import DigitalFile
from app.infrastructure.dynamic_tables import (
    create_template_table,
    drop_template_table,
)
from app.infrastructure.template_files import (
    create_template_excel,
    delete_template_excel,
)
from app.infrastructure.repositories import (
    DigitalFileRepository,
    TemplateColumnRepository,
    TemplateRepository,
)
from app.utils import now_in_app_timezone


def refresh_template_resources(
    session: Session,
    template_id: int,
    *,
    actor_id: int | None = None,
) -> None:
    """Regenerate the dynamic table and Excel template for ``template_id``."""

    template_repository = TemplateRepository(session)
    column_repository = TemplateColumnRepository(session)
    digital_repository = DigitalFileRepository(session)

    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    columns = list(column_repository.list_by_template(template_id))

    try:
        drop_template_table(template.table_name)
    except RuntimeError as exc:  # pragma: no cover - surfaced as validation error
        raise ValueError(str(exc)) from exc

    existing_file = digital_repository.get_by_template_id(template_id)
    if existing_file is not None:
        delete_template_excel(existing_file.path)
    digital_repository.delete_by_template_id(template_id)

    if not columns:
        return

    try:
        create_template_table(template.table_name, columns)
    except RuntimeError as exc:  # pragma: no cover - surfaced as validation error
        raise ValueError(str(exc)) from exc

    uploader_user_id = (
        actor_id
        or template.updated_by
        or template.created_by
        or 0
    )

    excel_info = create_template_excel(
        template.id,
        template.name,
        columns,
        user_id=uploader_user_id,
        table_name=template.table_name,
    )

    now = now_in_app_timezone()
    digital_repository.create(
        DigitalFile(
            id=None,
            template_id=template.id,
            name=excel_info.filename,
            description=template.description,
            path=excel_info.blob_path,
            created_by=actor_id,
            created_at=now,
            updated_by=None,
            updated_at=None,
        )
    )


__all__ = ["refresh_template_resources"]

