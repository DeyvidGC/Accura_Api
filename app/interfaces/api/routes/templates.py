"""Routes for managing templates and their columns."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.application.use_cases.template_columns import (
    create_template_column as create_template_column_uc,
    delete_template_column as delete_template_column_uc,
    get_template_column as get_template_column_uc,
    list_template_columns as list_template_columns_uc,
    update_template_column as update_template_column_uc,
)
from app.application.use_cases.templates import (
    create_template as create_template_uc,
    delete_template as delete_template_uc,
    get_template as get_template_uc,
    list_templates as list_templates_uc,
    update_template as update_template_uc,
    update_template_status as update_template_status_uc,
)
from app.domain.entities import Template, TemplateColumn, User
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import require_admin
from app.interfaces.api.schemas import (
    TemplateColumnCreate,
    TemplateColumnRead,
    TemplateColumnUpdate,
    TemplateCreate,
    TemplateRead,
    TemplateUpdate,
    TemplateStatusUpdate,
)

router = APIRouter(prefix="/templates", tags=["templates"])


def _template_to_read_model(template: Template) -> TemplateRead:
    if hasattr(TemplateRead, "model_validate"):
        return TemplateRead.model_validate(template)
    return TemplateRead.from_orm(template)


def _column_to_read_model(column: TemplateColumn) -> TemplateColumnRead:
    if hasattr(TemplateColumnRead, "model_validate"):
        return TemplateColumnRead.model_validate(column)
    return TemplateColumnRead.from_orm(column)


@router.post("/", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def register_template(
    template_in: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TemplateRead:
    """Create a new template definition."""

    try:
        template = create_template_uc(
            db,
            user_id=current_user.id,
            name=template_in.name,
            table_name=template_in.table_name,
            description=template_in.description,
            created_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _template_to_read_model(template)


@router.get("/", response_model=list[TemplateRead])
def list_templates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TemplateRead]:
    """Return a paginated list of templates."""

    templates = list_templates_uc(db, skip=skip, limit=limit)
    return [_template_to_read_model(template) for template in templates]


@router.get("/{template_id}", response_model=TemplateRead)
def read_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> TemplateRead:
    """Return the template identified by ``template_id``."""

    try:
        template = get_template_uc(db, template_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _template_to_read_model(template)


@router.put("/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: int,
    template_in: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TemplateRead:
    """Update an existing template."""

    if hasattr(template_in, "model_dump"):
        update_data = template_in.model_dump(exclude_unset=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        update_data = template_in.dict(exclude_unset=True)

    try:
        template = update_template_uc(
            db,
            template_id=template_id,
            name=update_data.get("name"),
            description=update_data.get("description"),
            status=update_data.get("status"),
            table_name=update_data.get("table_name"),
            is_active=update_data.get("is_active"),
            updated_by=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return _template_to_read_model(template)


@router.patch("/{template_id}/status", response_model=TemplateRead)
def update_template_status(
    template_id: int,
    status_in: TemplateStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TemplateRead:
    """Update only the status of an existing template."""

    try:
        template = update_template_status_uc(
            db,
            template_id=template_id,
            status=status_in.status,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return _template_to_read_model(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Response:
    """Delete a template and its dynamic table."""

    try:
        delete_template_uc(db, template_id, deleted_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{template_id}/columns",
    response_model=TemplateColumnRead,
    status_code=status.HTTP_201_CREATED,
)
def register_template_column(
    template_id: int,
    column_in: TemplateColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TemplateColumnRead:
    """Create a new column for the template."""

    try:
        column = create_template_column_uc(
            db,
            template_id=template_id,
            name=column_in.name,
            data_type=column_in.data_type,
            description=column_in.description,
            rule_id=column_in.rule_id,
            created_by=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Columna no encontrada"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return _column_to_read_model(column)


@router.get("/{template_id}/columns", response_model=list[TemplateColumnRead])
def list_template_columns(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TemplateColumnRead]:
    """Return all columns for a template."""

    try:
        columns = list_template_columns_uc(db, template_id=template_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_column_to_read_model(column) for column in columns]


@router.get(
    "/{template_id}/columns/{column_id}", response_model=TemplateColumnRead
)
def read_template_column(
    template_id: int,
    column_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> TemplateColumnRead:
    """Return a single template column."""

    try:
        column = get_template_column_uc(db, template_id=template_id, column_id=column_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _column_to_read_model(column)


@router.put(
    "/{template_id}/columns/{column_id}", response_model=TemplateColumnRead
)
def update_template_column(
    template_id: int,
    column_id: int,
    column_in: TemplateColumnUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TemplateColumnRead:
    """Update a template column definition."""

    if hasattr(column_in, "model_dump"):
        update_data = column_in.model_dump(exclude_unset=True)
    else:  # pragma: no cover - compatibility path for pydantic v1
        update_data = column_in.dict(exclude_unset=True)

    try:
        column = update_template_column_uc(
            db,
            template_id=template_id,
            column_id=column_id,
            name=update_data.get("name"),
            data_type=update_data.get("data_type"),
            description=update_data.get("description"),
            rule_id=update_data.get("rule_id"),
            is_active=update_data.get("is_active"),
            updated_by=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Columna no encontrada"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return _column_to_read_model(column)


@router.delete(
    "/{template_id}/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_template_column(
    template_id: int,
    column_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Response:
    """Delete a template column."""

    try:
        delete_template_column_uc(db, template_id=template_id, column_id=column_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
