"""Domain entity representing a data load executed by a user."""

from dataclasses import dataclass
from datetime import datetime

LOAD_STATUS_PROCESSING = "Procesando"
LOAD_STATUS_VALIDATED_SUCCESS = "Validado exitosamente"
LOAD_STATUS_VALIDATED_WITH_ERRORS = "Validado con errores"
LOAD_STATUS_FAILED = "Fallido"


@dataclass
class Load:
    """Metadata describing a data import performed against a template."""

    id: int | None
    template_id: int
    user_id: int
    status: str
    file_name: str
    total_rows: int
    error_rows: int
    report_path: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


__all__ = [
    "Load",
    "LOAD_STATUS_PROCESSING",
    "LOAD_STATUS_VALIDATED_SUCCESS",
    "LOAD_STATUS_VALIDATED_WITH_ERRORS",
    "LOAD_STATUS_FAILED",
]
