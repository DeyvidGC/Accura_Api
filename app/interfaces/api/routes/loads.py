"""Rutas de la API relacionadas con cargas de datos para plantillas."""

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.application.use_cases.loads import (
    get_load as get_load_uc,
    get_load_original_file as get_load_original_file_uc,
    get_load_report as get_load_report_uc,
    list_loads as list_loads_uc,
    process_template_load as process_template_load_uc,
    upload_template_load as upload_template_load_uc,
)
from app.domain.entities import Load, User
from app.infrastructure.database import SessionLocal, get_db
from app.interfaces.api.dependencies import get_current_active_user
from app.interfaces.api.schemas import LoadRead, LoadUploadResponse

router = APIRouter(tags=["loads"])
logger = logging.getLogger(__name__)


def _load_to_read_model(load: Load) -> LoadRead:
    if hasattr(LoadRead, "model_validate"):
        return LoadRead.model_validate(load)
    return LoadRead.from_orm(load)


@router.post(
    "/templates/{template_id}/loads",
    response_model=LoadUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template_load(
    template_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> LoadUploadResponse:
    """Sube información para la plantilla indicada y agenda su validación en segundo plano."""

    try:
        file_bytes = file.file.read()
    finally:
        file.file.seek(0)

    try:
        load = upload_template_load_uc(
            db,
            template_id=template_id,
            user=current_user,
            file_bytes=file_bytes,
            filename=file.filename or "",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if load.id is None:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible registrar la carga",
        )

    background_tasks.add_task(
        _process_load_in_background,
        load_id=load.id,
        template_id=template_id,
        user_id=current_user.id,
        file_bytes=file_bytes,
        filename=file.filename or "",
    )

    return LoadUploadResponse(
        message="Archivo cargado correctamente",
        load=_load_to_read_model(load),
    )


def _process_load_in_background(
    *,
    load_id: int,
    template_id: int,
    user_id: int,
    file_bytes: bytes,
    filename: str,
) -> None:
    """Procesa la carga utilizando una sesión de base de datos independiente."""

    session = SessionLocal()
    try:
        process_template_load_uc(
            session,
            load_id=load_id,
            template_id=template_id,
            user_id=user_id,
            file_bytes=file_bytes,
            filename=filename,
        )
    except Exception as exc:  # pragma: no cover - background processing guard
        logger.exception("Error al procesar la carga %s: %s", load_id, exc)
    finally:
        session.close()


@router.get("/loads", response_model=list[LoadRead])
def list_loads(
    template_id: int | None = Query(default=None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[LoadRead]:
    """Devuelve las cargas visibles para el usuario autenticado."""

    loads = list_loads_uc(
        db,
        current_user=current_user,
        template_id=template_id,
        skip=skip,
        limit=limit,
    )
    return [_load_to_read_model(load) for load in loads]


@router.get("/loads/{load_id}", response_model=LoadRead)
def read_load(
    load_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> LoadRead:
    """Obtiene la carga identificada por ``load_id`` si el usuario tiene acceso."""

    try:
        load = get_load_uc(db, load_id=load_id, current_user=current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _load_to_read_model(load)


@router.get("/loads/{load_id}/report")
def download_load_report(
    load_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Descarga el reporte en Excel generado para la carga solicitada."""

    try:
        load, path = get_load_report_uc(db, load_id=load_id, current_user=current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(
        path,
        filename=f"reporte_carga_{load.id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/loads/{load_id}/source")
def download_load_source_file(
    load_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Descarga el archivo original cargado por el usuario sin columnas adicionales."""

    try:
        load, path = get_load_original_file_uc(
            db, load_id=load_id, current_user=current_user
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    suffix = path.suffix.lower()
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if suffix == ".csv":
        media_type = "text/csv"

    return FileResponse(
        path,
        filename=f"carga_{load.id}_original{suffix}",
        media_type=media_type,
    )


__all__ = ["router"]
