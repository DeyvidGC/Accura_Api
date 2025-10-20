"""Database configuration and session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
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
