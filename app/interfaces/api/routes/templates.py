"""Rutas para administrar plantillas, sus columnas y accesos."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.application.use_cases.template_columns import (
    NewTemplateColumnData,
    create_template_column as create_template_column_uc,
    create_template_columns as create_template_columns_uc,
    delete_template_column as delete_template_column_uc,
    get_template_column as get_template_column_uc,
    list_template_columns as list_template_columns_uc,
    update_template_column as update_template_column_uc,
)
from app.application.use_cases.templates import (
    bulk_grant_template_access as bulk_grant_template_access_uc,
    bulk_revoke_template_access as bulk_revoke_template_access_uc,
    bulk_update_template_access as bulk_update_template_access_uc,
    create_template as create_template_uc,
    delete_template as delete_template_uc,
    get_template as get_template_uc,
    get_template_excel as get_template_excel_uc,
    list_template_access as list_template_access_uc,
    list_templates as list_templates_uc,
    update_template as update_template_uc,
    update_template_status as update_template_status_uc,
)
from app.domain.entities import Template, TemplateColumn, TemplateUserAccess, User
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import (
    get_current_active_user,
    require_admin,
)
from app.interfaces.api.schemas import (
    TemplateColumnBulkCreate,
    TemplateColumnCreate,
    TemplateColumnRead,
    TemplateColumnUpdate,
    TemplateCreate,
    TemplateRead,
    TemplateStatusUpdate,
    TemplateUpdate,
    TemplateUserAccessGrantList,
    TemplateUserAccessRead,
    TemplateUserAccessRevokeList,
    TemplateUserAccessUpdateList,
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


def _access_to_read_model(access: TemplateUserAccess) -> TemplateUserAccessRead:
    """Convert a ``TemplateUserAccess`` entity into the API read model."""

    if hasattr(TemplateUserAccessRead, "model_validate"):
        if isinstance(access, dict):  # pragma: no cover - compatibility path
            return TemplateUserAccessRead.model_validate(access)
        return TemplateUserAccessRead.model_validate(access, from_attributes=True)
    if isinstance(access, dict):  # pragma: no cover - compatibility for pydantic v1
        return TemplateUserAccessRead(**access)
    return TemplateUserAccessRead.from_orm(access)  # pragma: no cover


def _dump_model(model: object) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    raise TypeError("Unsupported model type for serialization")


@router.post("/", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
def register_template(
    template_in: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TemplateRead:
    """Crea una nueva definición de plantilla."""

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
    """Devuelve una lista paginada de plantillas registradas."""

    templates = list_templates_uc(db, skip=skip, limit=limit)
    return [_template_to_read_model(template) for template in templates]


@router.get("/{template_id}", response_model=TemplateRead)
def read_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> TemplateRead:
    """Obtiene la plantilla identificada por ``template_id``."""

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
    """Actualiza una plantilla existente."""

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
    """Actualiza únicamente el estado de una plantilla."""

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
    """Elimina una plantilla junto con su tabla dinámica."""

    try:
        delete_template_uc(db, template_id, deleted_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{template_id}/columns",
    response_model=TemplateColumnRead | list[TemplateColumnRead],
    status_code=status.HTTP_201_CREATED,
)
def register_template_column(
    template_id: int,
    column_in: TemplateColumnCreate
    | list[TemplateColumnCreate]
    | TemplateColumnBulkCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TemplateColumnRead | list[TemplateColumnRead]:
    """Crea una o varias columnas asociadas a la plantilla."""

    try:
        if isinstance(column_in, TemplateColumnCreate):
            column = create_template_column_uc(
                db,
                template_id=template_id,
                name=column_in.name,
                data_type=column_in.data_type,
                description=column_in.description,
                rule_id=column_in.rule_id,
                header=column_in.header,
                created_by=current_user.id,
            )
            result = _column_to_read_model(column)
        else:
            if isinstance(column_in, TemplateColumnBulkCreate):
                incoming_columns = column_in.columns
            else:
                incoming_columns = column_in
            payload = [
                NewTemplateColumnData(
                    name=col.name,
                    data_type=col.data_type,
                    description=col.description,
                    rule_id=col.rule_id,
                    rule_header=col.header,
                )
                for col in incoming_columns
            ]
            columns = create_template_columns_uc(
                db,
                template_id=template_id,
                columns=payload,
                created_by=current_user.id,
            )
            result = [_column_to_read_model(column) for column in columns]
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Columna no encontrada"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return result


@router.get("/{template_id}/columns", response_model=list[TemplateColumnRead])
def list_template_columns(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TemplateColumnRead]:
    """Lista todas las columnas configuradas para la plantilla."""

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
    """Obtiene la información de una columna específica."""

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
    """Actualiza la definición de una columna de plantilla."""

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
            header=update_data.get("header"),
            header_provided="header" in update_data,
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
    """Elimina una columna de la plantilla."""

    try:
        delete_template_column_uc(db, template_id=template_id, column_id=column_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/access",
    response_model=list[TemplateUserAccessRead],
    status_code=status.HTTP_201_CREATED,
)
def grant_template_accesses(
    payload: TemplateUserAccessGrantList,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TemplateUserAccessRead]:
    """Concede acceso a una o varias plantillas para los usuarios indicados."""

    try:
        accesses = bulk_grant_template_access_uc(
            db,
            grants=[_dump_model(item) for item in payload],
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Usuario no encontrado"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return [_access_to_read_model(access) for access in accesses]


@router.get(
    "/access",
    response_model=list[TemplateUserAccessRead],
)
def list_template_access(
    template_id: int = Query(..., ge=1),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TemplateUserAccessRead]:
    """Lista los accesos configurados para la plantilla solicitada."""

    try:
        accesses = list_template_access_uc(
            db,
            template_id=template_id,
            include_inactive=include_inactive,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [_access_to_read_model(access) for access in accesses]


@router.put(
    "/access",
    response_model=list[TemplateUserAccessRead],
)
def update_template_accesses(
    payload: TemplateUserAccessUpdateList,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TemplateUserAccessRead]:
    """Actualiza la ventana de acceso configurada para uno o varios accesos."""

    try:
        accesses = bulk_update_template_access_uc(
            db,
            updates=[_dump_model(item) for item in payload],
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Acceso no encontrado"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return [_access_to_read_model(access) for access in accesses]


@router.post(
    "/access/revoke",
    response_model=list[TemplateUserAccessRead],
)
def revoke_template_accesses(
    payload: TemplateUserAccessRevokeList,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[TemplateUserAccessRead]:
    """Revoca uno o varios accesos previamente concedidos."""

    try:
        accesses = bulk_revoke_template_access_uc(
            db,
            revocations=[_dump_model(item) for item in payload],
            revoked_by=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Acceso no encontrado"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return [_access_to_read_model(access) for access in accesses]


@router.get("/{template_id}/excel")
def download_template_excel(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Descarga el archivo de Excel generado para la plantilla."""

    try:
        path = get_template_excel_uc(
            db,
            template_id=template_id,
            requesting_user=current_user,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND
        if detail == "El usuario no tiene acceso a la plantilla":
            status_code = status.HTTP_403_FORBIDDEN
        elif detail not in {
            "Plantilla no encontrada",
            "Archivo de plantilla no encontrado",
        }:
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )
