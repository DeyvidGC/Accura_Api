"""Persistence helpers for notification entities."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from app.domain.entities import Notification
from app.infrastructure.models import NotificationModel


class NotificationRepository:
    """Provide CRUD operations for :class:`Notification` objects."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, recipient_id: int, *, limit: int | None = 50) -> Sequence[Notification]:
        query = (
            self.session.query(NotificationModel)
            .filter(NotificationModel.recipient_id == recipient_id)
            .order_by(NotificationModel.created_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def list_unread_for_user(
        self, recipient_id: int, *, limit: int | None = 50
    ) -> Sequence[Notification]:
        query = (
            self.session.query(NotificationModel)
            .filter(NotificationModel.recipient_id == recipient_id)
            .filter(NotificationModel.read_at.is_(None))
            .order_by(NotificationModel.created_at.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def create(self, notification: Notification) -> Notification:
        model = NotificationModel()
        self._apply_entity_to_model(model, notification, include_creation_fields=True)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_entity(model)

    def mark_as_read(self, notification_ids: Iterable[int], *, user_id: int) -> None:
        ids = [notification_id for notification_id in notification_ids if notification_id is not None]
        if not ids:
            return
        self.session.query(NotificationModel).filter(
            NotificationModel.id.in_(ids),
            NotificationModel.recipient_id == user_id,
        ).update({NotificationModel.read_at: datetime.utcnow()}, synchronize_session=False)
        self.session.commit()

    @staticmethod
    def _apply_entity_to_model(
        model: NotificationModel,
        notification: Notification,
        *,
        include_creation_fields: bool,
    ) -> None:
        if include_creation_fields:
            model.created_at = notification.created_at or datetime.utcnow()
        model.recipient_id = notification.recipient_id
        model.event_type = notification.event_type
        model.title = notification.title
        model.message = notification.message
        model.payload = notification.payload or {}
        model.read_at = notification.read_at

    @staticmethod
    def _to_entity(model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            recipient_id=model.recipient_id,
            event_type=model.event_type,
            title=model.title,
            message=model.message,
            payload=model.payload or {},
            created_at=model.created_at,
            read_at=model.read_at,
        )


__all__ = ["NotificationRepository"]
