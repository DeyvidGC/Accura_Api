"""Use case for creating template columns."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import TemplateColumn
from app.infrastructure.dynamic_tables import ensure_data_type
from app.infrastructure.repositories import (
    RuleRepository,
    TemplateColumnRepository,
    TemplateRepository,
)

from .naming import derive_column_identifier, normalize_column_display_name
from .validators import (
    ensure_rule_header_dependencies,
    normalize_rule_header,
    normalize_rule_ids,
)


@dataclass(frozen=True)
class NewTemplateColumnData:
    """Data required to create a template column."""

    name: str
    data_type: str
    description: str | None = None
    rule_ids: Sequence[int] | None = None
    rule_header: Sequence[str] | None = None


def _ensure_template_is_editable(template_repository: TemplateRepository, template_id: int):
    template = template_repository.get(template_id)
    if template is None:
        raise ValueError("Plantilla no encontrada")

    if template.status == "published":
        raise ValueError("No se pueden modificar las columnas de una plantilla publicada")

    return template


def _build_column(
    *,
    template_id: int,
    payload: NewTemplateColumnData,
    created_by: int | None,
    forbidden_names: set[str],
    forbidden_identifiers: set[str],
) -> TemplateColumn:
    normalized_name = normalize_column_display_name(payload.name)
    identifier = derive_column_identifier(normalized_name)

    normalized_key = normalized_name.lower()
    if normalized_key in forbidden_names or identifier in forbidden_identifiers:
        raise ValueError("Ya existe una columna con ese nombre en la plantilla")

    forbidden_names.add(normalized_key)
    forbidden_identifiers.add(identifier)

    try:
        normalized_type = ensure_data_type(payload.data_type)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    now = datetime.utcnow()
    normalized_header = normalize_rule_header(payload.rule_header)
    normalized_rule_ids = normalize_rule_ids(payload.rule_ids)

    return TemplateColumn(
        id=None,
        template_id=template_id,
        rule_ids=normalized_rule_ids,
        rule_header=normalized_header,
        name=normalized_name,
        description=payload.description,
        data_type=normalized_type,
        created_by=created_by,
        created_at=now,
        updated_by=None,
        updated_at=None,
        is_active=True,
        deleted=False,
        deleted_by=None,
        deleted_at=None,
    )


def create_template_column(
    session: Session,
    *,
    template_id: int,
    name: str,
    data_type: str,
    description: str | None = None,
    rule_ids: Sequence[int] | None = None,
    header: Sequence[str] | None = None,
    created_by: int | None = None,
) -> TemplateColumn:
    """Create a new column inside a template.

    Raises:
        ValueError: If the template does not exist or is already published.
    """

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)
    rule_repository = RuleRepository(session)

    _ensure_template_is_editable(template_repository, template_id)

    existing_columns = list(column_repository.list_by_template(template_id))
    forbidden_names = {column.name.lower() for column in existing_columns}
    forbidden_identifiers = {
        derive_column_identifier(column.name) for column in existing_columns
    }
    column = _build_column(
        template_id=template_id,
        payload=NewTemplateColumnData(
            name=name,
            data_type=data_type,
            description=description,
            rule_ids=rule_ids,
            rule_header=header,
        ),
        created_by=created_by,
        forbidden_names=forbidden_names,
        forbidden_identifiers=forbidden_identifiers,
    )

    ensure_rule_header_dependencies(
        columns=[*existing_columns, column],
        rule_repository=rule_repository,
    )

    saved_column = column_repository.create(column)

    return saved_column


def create_template_columns(
    session: Session,
    *,
    template_id: int,
    columns: Sequence[NewTemplateColumnData],
    created_by: int | None = None,
) -> list[TemplateColumn]:
    """Create multiple columns for a template in a single operation."""

    if not columns:
        return []

    column_repository = TemplateColumnRepository(session)
    template_repository = TemplateRepository(session)
    rule_repository = RuleRepository(session)

    _ensure_template_is_editable(template_repository, template_id)

    existing_columns = list(column_repository.list_by_template(template_id))
    forbidden_names = {column.name.lower() for column in existing_columns}
    forbidden_identifiers = {
        derive_column_identifier(column.name) for column in existing_columns
    }

    new_columns: list[TemplateColumn] = []
    for payload in columns:
        column = _build_column(
            template_id=template_id,
            payload=payload,
            created_by=created_by,
            forbidden_names=forbidden_names,
            forbidden_identifiers=forbidden_identifiers,
        )
        new_columns.append(column)

    ensure_rule_header_dependencies(
        columns=[*existing_columns, *new_columns],
        rule_repository=rule_repository,
    )

    return column_repository.create_many(new_columns)
