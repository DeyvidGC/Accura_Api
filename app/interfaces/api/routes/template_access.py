"""Rutas para operaciones masivas de accesos a plantillas."""

from collections.abc import Iterable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.use_cases.templates import (
    bulk_grant_template_access as bulk_grant_template_access_uc,
    bulk_revoke_template_access as bulk_revoke_template_access_uc,
    bulk_update_template_access as bulk_update_template_access_uc,
)
from app.domain.entities import TemplateUserAccess, User
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import require_admin
from app.interfaces.api.schemas import (
    TemplateUserAccessGrantList,
    TemplateUserAccessRead,
    TemplateUserAccessRevokeList,
    TemplateUserAccessUpdateList,
)

router = APIRouter(prefix="/template-access", tags=["template-access"])


def _access_to_read_model(access: TemplateUserAccess) -> TemplateUserAccessRead:
    if hasattr(TemplateUserAccessRead, "model_validate"):
        return TemplateUserAccessRead.model_validate(access)
    return TemplateUserAccessRead.from_orm(access)


def _dump_items(items: Iterable) -> list[dict]:
    dumped: list[dict] = []
    for item in items:
        if hasattr(item, "model_dump"):
            dumped.append(item.model_dump())
        else:  # pragma: no cover - compatibility path for pydantic v1
            dumped.append(item.dict())
    return dumped


@router.post(
    "/grants",
    response_model=list[TemplateUserAccessRead],
    status_code=status.HTTP_201_CREATED,
)
def bulk_grant_template_access(
    payload: TemplateUserAccessGrantList,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TemplateUserAccessRead]:
    """Concede accesos a múltiples plantillas en una sola operación."""

    try:
        accesses = bulk_grant_template_access_uc(
            db,
            grants=_dump_items(payload),
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Usuario no encontrado"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return [_access_to_read_model(access) for access in accesses]


@router.post(
    "/revocations",
    response_model=list[TemplateUserAccessRead],
)
def bulk_revoke_template_access(
    payload: TemplateUserAccessRevokeList,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[TemplateUserAccessRead]:
    """Revoca múltiples accesos previamente concedidos."""

    try:
        accesses = bulk_revoke_template_access_uc(
            db,
            revocations=_dump_items(payload),
            revoked_by=current_user.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Acceso no encontrado"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return [_access_to_read_model(access) for access in accesses]


@router.post(
    "/updates",
    response_model=list[TemplateUserAccessRead],
)
def bulk_update_template_access(
    payload: TemplateUserAccessUpdateList,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[TemplateUserAccessRead]:
    """Actualiza la vigencia de múltiples accesos existentes."""

    try:
        accesses = bulk_update_template_access_uc(
            db,
            updates=_dump_items(payload),
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_400_BAD_REQUEST
        if detail in {"Plantilla no encontrada", "Acceso no encontrado"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return [_access_to_read_model(access) for access in accesses]


__all__ = ["router"]
