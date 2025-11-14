"""SQLAlchemy model for audit records of template table operations."""

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.mssql import JSON as MSSQLJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.infrastructure.database import Base

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
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())


__all__ = ["AuditLogModel"]
