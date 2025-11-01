"""Database configuration and session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


settings = get_settings()
connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url, pool_pre_ping=True, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ensure_rule_header_column() -> None:
    """Add missing ``rule_header`` column to ``template_column`` table if needed."""

    inspector = inspect(engine)
    if not inspector.has_table("template_column"):
        return

    columns = {column["name"] for column in inspector.get_columns("template_column")}
    if "rule_header" in columns:
        return

    from app.infrastructure.models.template_column import TemplateColumnModel

    column = TemplateColumnModel.__table__.c.rule_header
    column_type = column.type.compile(dialect=engine.dialect)
    statement = text(
        f"ALTER TABLE template_column ADD COLUMN rule_header {column_type}"
    )

    with engine.begin() as connection:
        connection.execute(statement)


def initialize_database() -> None:
    """Ensure all ORM models have corresponding database tables."""

    from app.infrastructure import models  # noqa: F401  # ensure models are imported

    _ensure_rule_header_column()
    Base.metadata.create_all(bind=engine, checkfirst=True)


def get_db() -> Generator:
    """Yield a database session and close it afterwards."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


initialize_database()
