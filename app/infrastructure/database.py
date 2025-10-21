"""Database configuration and session management."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


def _create_engine() -> Engine:
    settings = get_settings()
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(
        settings.database_url, pool_pre_ping=True, connect_args=connect_args
    )


@lru_cache
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine configured from environment settings."""

    return _create_engine()


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached session factory bound to the configured engine."""

    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def initialize_database() -> None:
    """Ensure all ORM models have corresponding database tables."""

    from app.infrastructure import models  # noqa: F401  # ensure models are imported

    Base.metadata.create_all(bind=get_engine(), checkfirst=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it afterwards."""

    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
