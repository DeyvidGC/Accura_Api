"""SQLAlchemy model for template columns."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.dialects.mssql import JSON as MSSQLJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from sqlalchemy.sql import expression

from app.infrastructure.database import Base
from app.infrastructure.models.rule import RuleModel
from app.utils import now_in_app_naive_datetime

_header_json_type = (
    JSONB().with_variant(JSON(), "sqlite").with_variant(MSSQLJSON(), "mssql")
)


template_column_rule_table = Table(
    "template_column_rule",
    Base.metadata,
    Column(
        "template_column_id",
        Integer,
        ForeignKey("template_column.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "rule_id",
        Integer,
        ForeignKey("rule.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


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
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    data_type = Column(String(50), nullable=False)
    rule_header = Column(_header_json_type, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(), nullable=False, default=now_in_app_naive_datetime)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime(), nullable=True, onupdate=now_in_app_naive_datetime
    )
    is_active = Column(Boolean, nullable=False, default=True)
    deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    deleted_by = Column(Integer, nullable=True)
    deleted_at = Column(DateTime(), nullable=True)

    template = relationship("TemplateModel", back_populates="columns")
    rules = relationship(
        RuleModel,
        secondary=template_column_rule_table,
        lazy="joined",
        order_by=RuleModel.id,
    )


__all__ = ["TemplateColumnModel", "template_column_rule_table"]
