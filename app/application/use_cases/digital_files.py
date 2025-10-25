"""Use cases for interacting with stored digital files."""

from sqlalchemy.orm import Session

from app.domain.entities import DigitalFile
from app.infrastructure.repositories import DigitalFileRepository


def list_digital_files(
    session: Session,
    *,
    template_id: int | None = None,
    skip: int = 0,
    limit: int | None = 100,
) -> list[DigitalFile]:
    """Return digital files optionally filtered by template identifier."""

    repository = DigitalFileRepository(session)
    return repository.list(template_id=template_id, skip=skip, limit=limit)


def get_digital_file(session: Session, digital_file_id: int) -> DigitalFile:
    """Return a digital file identified by ``digital_file_id`` or raise an error."""

    repository = DigitalFileRepository(session)
    digital_file = repository.get(digital_file_id)
    if digital_file is None:
        raise ValueError("Archivo digital no encontrado")
    return digital_file


def get_digital_file_by_template(session: Session, template_id: int) -> DigitalFile:
    """Return the digital file associated with ``template_id`` or raise an error."""

    repository = DigitalFileRepository(session)
    digital_file = repository.get_by_template_id(template_id)
    if digital_file is None:
        raise ValueError("Archivo digital no encontrado")
    return digital_file


__all__ = [
    "list_digital_files",
    "get_digital_file",
    "get_digital_file_by_template",
]
