"""SQLAlchemy model for validation rules."""

from sqlalchemy import Column, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.infrastructure.database import Base

_rule_json_type = JSONB().with_variant(JSON(), "sqlite")


class RuleModel(Base):
    """Database representation of validation rules."""

    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    rule = Column(_rule_json_type, nullable=False)


__all__ = ["RuleModel"]
