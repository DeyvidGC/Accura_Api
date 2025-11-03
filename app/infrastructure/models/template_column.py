"""SQLAlchemy model for template columns."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from sqlalchemy.sql import expression

from app.infrastructure.database import Base

_header_json_type = JSONB().with_variant(JSON(), "sqlite")


class TemplateColumnModel(Base):
    """Database representation of a template column definition."""

    __tablename__ = "template_column"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("template.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(Integer, ForeignKey("rule.id"), nullable=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    data_type = Column(String(50), nullable=False)
    rule_header = Column(_header_json_type, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)
    deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    deleted_by = Column(Integer, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    template = relationship("TemplateModel", back_populates="columns")
    rule = relationship("RuleModel", lazy="joined")


__all__ = ["TemplateColumnModel"]
