"""Rutas para obtener indicadores KPI del sistema."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.domain.entities import User
from app.application.use_cases.kpis import (
    ClientKPIReport,
    KPIReport,
    get_client_kpis,
    get_kpis,
)
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import get_current_active_user, require_admin
from app.interfaces.api.schemas import ClientKPIReportRead, KPIReportRead

router = APIRouter(prefix="/kpis", tags=["kpis"])


def _report_to_read_model(report: KPIReport) -> KPIReportRead:
    if hasattr(KPIReportRead, "model_validate"):
        return KPIReportRead.model_validate(report)
    return KPIReportRead.from_orm(report)


def _client_report_to_read_model(report: ClientKPIReport) -> ClientKPIReportRead:
    if hasattr(ClientKPIReportRead, "model_validate"):
        return ClientKPIReportRead.model_validate(report)
    return ClientKPIReportRead.from_orm(report)


@router.get("/", response_model=KPIReportRead)
def read_kpis(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> KPIReportRead:
    """Devuelve los indicadores clave de desempeño para el mes en curso."""

    report = get_kpis(db, admin_user_id=current_admin.id)
    return _report_to_read_model(report)


@router.get("/client", response_model=ClientKPIReportRead)
def read_client_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClientKPIReportRead:
    """Devuelve los indicadores clave de desempeño específicos para el usuario."""

    report = get_client_kpis(db, user_id=current_user.id)
    return _client_report_to_read_model(report)


__all__ = ["router"]
