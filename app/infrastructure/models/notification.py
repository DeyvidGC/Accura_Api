"""SQLAlchemy model for persisted notifications."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base
from app.utils import now_in_app_timezone


class NotificationModel(Base):
    """Database representation for user notifications."""

    __tablename__ = "notification"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    title = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=now_in_app_timezone
    )
    read_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("UserModel", lazy="joined")


__all__ = ["NotificationModel"]
