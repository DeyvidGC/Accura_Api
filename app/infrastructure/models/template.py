"""SQLAlchemy model for templates."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base


class TemplateModel(Base):
    """Database representation of a template definition."""

    __tablename__ = "template"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="unpublished")
    description = Column(String(255), nullable=True)
    table_name = Column(String(63), nullable=False, unique=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)

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
