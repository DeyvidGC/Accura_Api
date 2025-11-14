"""Persistence helpers for notification entities."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Iterable

from sqlalchemy.orm import Session

from app.domain.entities import Notification
from app.infrastructure.models import NotificationModel
from app.utils import (
    ensure_app_naive_datetime,
    ensure_app_timezone,
    now_in_app_timezone,
)


class NotificationRepository:
    """Provide CRUD operations for :class:`Notification` objects."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(
        self,
        user_id: int,
        *,
        limit: int | None = 50,
    ) -> Sequence[Notification]:
        query = self.session.query(NotificationModel)
        query = query.filter(NotificationModel.user_id == user_id)
        query = query.order_by(
            NotificationModel.created_at.desc(), NotificationModel.id.desc()
        )
        if limit is not None:
            query = query.limit(limit)
        return [self._to_entity(model) for model in query.all()]

    def list_unread_for_user(
        self, user_id: int, *, limit: int | None = 50
    ) -> Sequence[Notification]:
        query = (
            self.session.query(NotificationModel)
            .filter(NotificationModel.user_id == user_id)
            .filter(NotificationModel.read_at.is_(None))
            .order_by(
                NotificationModel.created_at.desc(), NotificationModel.id.desc()
            )
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

    def update(self, notification: Notification) -> Notification:
        if notification.id is None:
            raise ValueError("Notification id is required for updates")
        model = self.session.get(NotificationModel, notification.id)
        if model is None:
            msg = f"Notification with id {notification.id} not found"
            raise ValueError(msg)
        self._apply_entity_to_model(model, notification, include_creation_fields=False)
        if notification.created_at is not None:
            model.created_at = ensure_app_naive_datetime(notification.created_at)
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
            NotificationModel.user_id == user_id,
        ).update(
            {
                NotificationModel.read_at: ensure_app_naive_datetime(
                    now_in_app_timezone()
                )
            },
            synchronize_session=False,
        )
        self.session.commit()

    def get_latest_by_user_and_load(
        self, *, user_id: int, load_id: int
    ) -> Notification | None:
        query = (
            self.session.query(NotificationModel)
            .filter(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
        )
        for model in query.all():
            payload = model.payload or {}
            try:
                payload_load_id = int(payload.get("load_id"))
            except (TypeError, ValueError):
                continue
            if payload_load_id == load_id:
                return self._to_entity(model)
        return None

    @staticmethod
    def _apply_entity_to_model(
        model: NotificationModel,
        notification: Notification,
        *,
        include_creation_fields: bool,
    ) -> None:
        if include_creation_fields:
            model.created_at = (
                ensure_app_naive_datetime(notification.created_at)
                or ensure_app_naive_datetime(now_in_app_timezone())
            )
        model.user_id = notification.user_id
        model.event_type = notification.event_type
        model.title = notification.title
        model.message = notification.message
        model.payload = notification.payload or {}
        model.read_at = ensure_app_naive_datetime(notification.read_at)

    @staticmethod
    def _to_entity(model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            user_id=model.user_id,
            event_type=model.event_type,
            title=model.title,
            message=model.message,
            payload=model.payload or {},
            created_at=ensure_app_timezone(model.created_at),
            read_at=ensure_app_timezone(model.read_at),
        )


__all__ = ["NotificationRepository"]
