"""Use case for computing KPI metrics for administrative dashboards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.entities import (
    LOAD_STATUS_VALIDATED_SUCCESS,
    LOAD_STATUS_VALIDATED_WITH_ERRORS,
)
from app.infrastructure.models import LoadModel, TemplateModel, UserModel


@dataclass
class MonthlyComparison:
    """Represents a metric comparing the current month against the previous one."""

    current_month: int
    previous_month: int


@dataclass
class TemplatePublicationSummary:
    """Summary of published vs unpublished templates."""

    published: int
    unpublished: int


@dataclass
class ValidationEffectiveness:
    """Aggregated information about validation outcomes for the current month."""

    successful: int
    total: int
    effectiveness_percentage: float


@dataclass
class KPIReport:
    """Aggregate view of KPI metrics used in dashboards."""

    active_users: MonthlyComparison
    templates: TemplatePublicationSummary
    loads: MonthlyComparison
    validations: ValidationEffectiveness


def _month_boundaries(reference: datetime) -> tuple[datetime, datetime]:
    """Return the start of the reference month and the start of the following month."""

    start = reference.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return start, next_month


def _previous_month_start(current_start: datetime) -> datetime:
    """Return the start datetime of the month preceding ``current_start``."""

    if current_start.month == 1:
        return current_start.replace(year=current_start.year - 1, month=12)
    return current_start.replace(month=current_start.month - 1)


def get_kpis(session: Session, *, reference: datetime | None = None) -> KPIReport:
    """Compute KPI metrics required by the administrative dashboard."""

    now = reference or datetime.utcnow()
    current_start, next_month_start = _month_boundaries(now)
    previous_start = _previous_month_start(current_start)
    previous_end = current_start

    active_users_current = (
        session.query(func.count(UserModel.id))
        .filter(
            UserModel.is_active.is_(True),
            UserModel.last_login.isnot(None),
            UserModel.last_login >= current_start,
            UserModel.last_login < next_month_start,
        )
        .scalar()
    ) or 0

    active_users_previous = (
        session.query(func.count(UserModel.id))
        .filter(
            UserModel.is_active.is_(True),
            UserModel.last_login.isnot(None),
            UserModel.last_login >= previous_start,
            UserModel.last_login < previous_end,
        )
        .scalar()
    ) or 0

    published_templates = (
        session.query(func.count(TemplateModel.id))
        .filter(TemplateModel.status == "published")
        .scalar()
    ) or 0

    unpublished_templates = (
        session.query(func.count(TemplateModel.id))
        .filter(
            (TemplateModel.status != "published")
            | (TemplateModel.status.is_(None))
        )
        .scalar()
    ) or 0

    loads_current = (
        session.query(func.count(LoadModel.id))
        .filter(
            LoadModel.created_at >= current_start,
            LoadModel.created_at < next_month_start,
        )
        .scalar()
    ) or 0

    loads_previous = (
        session.query(func.count(LoadModel.id))
        .filter(
            LoadModel.created_at >= previous_start,
            LoadModel.created_at < previous_end,
        )
        .scalar()
    ) or 0

    completed_statuses = (
        LOAD_STATUS_VALIDATED_SUCCESS,
        LOAD_STATUS_VALIDATED_WITH_ERRORS,
    )

    successful_validations = (
        session.query(func.count(LoadModel.id))
        .filter(
            LoadModel.status == LOAD_STATUS_VALIDATED_SUCCESS,
            LoadModel.finished_at.isnot(None),
            LoadModel.finished_at >= current_start,
            LoadModel.finished_at < next_month_start,
        )
        .scalar()
    ) or 0

    total_validations = (
        session.query(func.count(LoadModel.id))
        .filter(
            LoadModel.status.in_(completed_statuses),
            LoadModel.finished_at.isnot(None),
            LoadModel.finished_at >= current_start,
            LoadModel.finished_at < next_month_start,
        )
        .scalar()
    ) or 0

    effectiveness = (
        (successful_validations / total_validations) * 100 if total_validations else 0.0
    )

    return KPIReport(
        active_users=MonthlyComparison(
            current_month=int(active_users_current),
            previous_month=int(active_users_previous),
        ),
        templates=TemplatePublicationSummary(
            published=int(published_templates),
            unpublished=int(unpublished_templates),
        ),
        loads=MonthlyComparison(
            current_month=int(loads_current),
            previous_month=int(loads_previous),
        ),
        validations=ValidationEffectiveness(
            successful=int(successful_validations),
            total=int(total_validations),
            effectiveness_percentage=float(round(effectiveness, 2)),
        ),
    )


__all__ = [
    "KPIReport",
    "MonthlyComparison",
    "TemplatePublicationSummary",
    "ValidationEffectiveness",
    "get_kpis",
]
