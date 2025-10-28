"""SQLAlchemy model for persisted notifications."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base


class NotificationModel(Base):
    """Database representation for user notifications."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    title = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    read_at = Column(DateTime, nullable=True)

    recipient = relationship("UserModel", lazy="joined")


__all__ = ["NotificationModel"]
