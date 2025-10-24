"""SQLAlchemy model for validation rules."""

from sqlalchemy import Boolean, Column, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.infrastructure.database import Base

_rule_json_type = JSONB().with_variant(JSON(), "sqlite")


class RuleModel(Base):
    """Database representation of validation rules."""

    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    rule = Column(_rule_json_type, nullable=False)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)


__all__ = ["RuleModel"]
