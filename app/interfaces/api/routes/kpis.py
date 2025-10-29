"""Rutas para obtener indicadores KPI del sistema."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.domain.entities import User
from app.application.use_cases.kpis import KPIReport, get_kpis
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import require_admin
from app.interfaces.api.schemas import KPIReportRead

router = APIRouter(prefix="/kpis", tags=["kpis"])


def _report_to_read_model(report: KPIReport) -> KPIReportRead:
    if hasattr(KPIReportRead, "model_validate"):
        return KPIReportRead.model_validate(report)
    return KPIReportRead.from_orm(report)


@router.get("/", response_model=KPIReportRead)
def read_kpis(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> KPIReportRead:
    """Devuelve los indicadores clave de desempeño para el mes en curso."""

    report = get_kpis(db, admin_user_id=current_admin.id)
    return _report_to_read_model(report)


__all__ = ["router"]
