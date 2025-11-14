"""SQLAlchemy model for audit records of template table operations."""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.mssql import JSON as MSSQLJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.infrastructure.database import Base
from app.utils import now_in_app_timezone

_audit_json_type = (
    JSONB().with_variant(JSON(), "sqlite").with_variant(MSSQLJSON(), "mssql")
)


class AuditLogModel(Base):
    """Database representation of audit events."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(63), nullable=False)
    columns = Column(_audit_json_type, nullable=False)
    operation = Column(String(50), nullable=False)
    created_by = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=now_in_app_timezone
    )
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=True, onupdate=now_in_app_timezone
    )


__all__ = ["AuditLogModel"]
