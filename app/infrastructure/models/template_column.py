"""SQLAlchemy model for template columns."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base


class TemplateColumnModel(Base):
    """Database representation of a template column definition."""

    __tablename__ = "template_columns"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    data_type = Column(String(50), nullable=False)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)

    template = relationship("TemplateModel", back_populates="columns")
    rule = relationship("RuleModel", lazy="joined")


__all__ = ["TemplateColumnModel"]
