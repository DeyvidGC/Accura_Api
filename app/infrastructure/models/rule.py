"""SQLAlchemy model for validation rules."""

from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.sql import expression
from sqlalchemy.dialects.mssql import JSON as MSSQLJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.infrastructure.database import Base
from app.utils import now_in_app_timezone

_rule_json_type = (
    JSONB().with_variant(JSON(), "sqlite").with_variant(MSSQLJSON(), "mssql")
)


class RuleModel(Base):
    """Database representation of validation rules."""

    __tablename__ = "rule"

    id = Column(Integer, primary_key=True, index=True)
    rule = Column(_rule_json_type, nullable=False)
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


__all__ = ["RuleModel"]
