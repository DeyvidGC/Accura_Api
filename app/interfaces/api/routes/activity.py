"""Endpoints providing recent activity information."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.use_cases.activity import get_recent_activity
from app.domain.entities import ActivityEvent, User
from app.infrastructure.database import get_db
from app.interfaces.api.dependencies import require_admin
from app.interfaces.api.schemas import RecentActivityRead

router = APIRouter(prefix="/activity", tags=["activity"])


def _event_to_schema(event: ActivityEvent) -> RecentActivityRead:
    return RecentActivityRead(
        event_id=event.event_id,
        event_type=event.event_type,
        summary=event.summary,
        created_at=event.created_at,
        metadata=event.metadata,
    )


@router.get("/recent", response_model=list[RecentActivityRead])
def read_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Número máximo de eventos a retornar"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[RecentActivityRead]:
    """Return the most recent activity events visible to administrators."""

    events = get_recent_activity(db, limit=limit)
    return [_event_to_schema(event) for event in events]


__all__ = ["router"]
