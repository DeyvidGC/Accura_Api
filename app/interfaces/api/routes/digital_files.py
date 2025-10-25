"""Routes exposing stored digital file metadata."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.use_cases.digital_files import (
    get_digital_file as get_digital_file_uc,
    get_digital_file_by_template as get_digital_file_by_template_uc,
    list_digital_files as list_digital_files_uc,
)
from app.domain.entities import DigitalFile, User
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import require_admin
from app.interfaces.api.schemas import DigitalFileRead

router = APIRouter(prefix="/digital-files", tags=["digital_files"])


def _digital_file_to_read_model(digital_file: DigitalFile) -> DigitalFileRead:
    if hasattr(DigitalFileRead, "model_validate"):
        return DigitalFileRead.model_validate(digital_file)
    return DigitalFileRead.from_orm(digital_file)


@router.get("/", response_model=list[DigitalFileRead])
def list_digital_files(
    template_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[DigitalFileRead]:
    """Return stored digital files optionally filtered by template."""

    digital_files = list_digital_files_uc(
        db, template_id=template_id, skip=skip, limit=limit
    )
    return [_digital_file_to_read_model(digital_file) for digital_file in digital_files]


@router.get("/{digital_file_id}", response_model=DigitalFileRead)
def read_digital_file(
    digital_file_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DigitalFileRead:
    """Return a digital file identified by ``digital_file_id``."""

    try:
        digital_file = get_digital_file_uc(db, digital_file_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _digital_file_to_read_model(digital_file)


@router.get("/by-template/{template_id}", response_model=DigitalFileRead)
def read_digital_file_by_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DigitalFileRead:
    """Return the digital file associated with ``template_id``."""

    try:
        digital_file = get_digital_file_by_template_uc(db, template_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _digital_file_to_read_model(digital_file)


__all__ = [
    "router",
]
