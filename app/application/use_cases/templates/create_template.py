"""Use case for creating templates."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import Template
from app.application.use_cases.notifications import notify_template_created
from app.infrastructure.dynamic_tables import IdentifierError, ensure_identifier
from app.infrastructure.repositories import TemplateRepository

DEFAULT_TEMPLATE_STATUS = "unpublished"


def create_template(
    session: Session,
    *,
    user_id: int,
    name: str,
    table_name: str,
    description: str | None = None,
    created_by: int | None = None,
) -> Template:
    """Create a new template with status ``unpublished``."""

    repository = TemplateRepository(session)

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("El nombre de la plantilla no puede estar vacío")

    try:
        safe_table_name = ensure_identifier(table_name, kind="table")
    except IdentifierError as exc:
        raise ValueError(str(exc)) from exc

    existing = repository.get_by_table_name(safe_table_name)
    if existing is not None:
        raise ValueError("El nombre de la tabla ya está en uso")

    existing_by_name = repository.get_by_name(normalized_name)
    if existing_by_name is not None:
        raise ValueError("El nombre de la plantilla ya está en uso")

    now = datetime.utcnow()
    template = Template(
        id=None,
        user_id=user_id,
        name=normalized_name,
        status=DEFAULT_TEMPLATE_STATUS,
        description=description,
        table_name=safe_table_name,
        created_by=created_by,
        created_at=now,
        updated_by=None,
        updated_at=None,
        is_active=True,
        deleted=False,
        deleted_by=None,
        deleted_at=None,
    )

    saved_template = repository.create(template)
    notify_template_created(session, template=saved_template)
    return saved_template
