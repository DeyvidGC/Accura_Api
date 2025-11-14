"""SQLAlchemy model for templates."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from app.infrastructure.database import Base
from app.utils import now_in_app_timezone


class TemplateModel(Base):
    """Database representation of a template definition."""

    __tablename__ = "template"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="unpublished")
    description = Column(String(255), nullable=True)
    table_name = Column(String(63), nullable=False)
    created_by = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=now_in_app_timezone
    )
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=True, onupdate=now_in_app_timezone
    )
    is_active = Column(Boolean, nullable=False, default=True)
    deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    deleted_by = Column(Integer, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("UserModel", lazy="joined")
    columns = relationship(
        "TemplateColumnModel",
        back_populates="template",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    access_records = relationship(
        "TemplateUserAccessModel",
        back_populates="template",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


__all__ = ["TemplateModel"]
