"""Database configuration and session management."""

from __future__ import annotations

from collections.abc import Generator

from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


settings = get_settings()


def _resolve_database_url(raw_url: str) -> str:
    """Return a SQLAlchemy-compatible URL for the configured database."""

    normalized = raw_url.lstrip()
    if normalized.lower().startswith("driver="):
        # Allow plain ODBC connection strings such as those provided by Azure SQL.
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(normalized)}"
    return raw_url


database_url = _resolve_database_url(settings.database_url)
connect_args: dict[str, object] = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database() -> None:
    """Ensure all ORM models have corresponding database tables."""

    from app.infrastructure import models  # noqa: F401  # ensure models are imported

    Base.metadata.create_all(bind=engine, checkfirst=True)


def get_db() -> Generator:
    """Yield a database session and close it afterwards."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


initialize_database()
