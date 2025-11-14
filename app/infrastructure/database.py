"""Database configuration and session management."""

from __future__ import annotations

from collections.abc import Generator, Sequence

import logging
import re
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


settings = get_settings()

logger = logging.getLogger(__name__)

_ODBC_DRIVER_PATTERN = re.compile(r"(?i)driver\s*=\s*(\{[^}]+\}|[^;]+)")


def _pick_best_sql_server_driver(installed: Sequence[str]) -> str | None:
    """Return the newest installed SQL Server ODBC driver."""

    if not installed:
        return None

    def driver_sort_key(name: str) -> tuple[int, str]:
        version_match = re.search(r"(\d+)", name)
        version = int(version_match.group(1)) if version_match else -1
        return (version, name)

    return sorted(installed, key=driver_sort_key)[-1]


def _ensure_sql_server_driver(raw_connection: str) -> str:
    """Ensure the ODBC driver referenced in the connection string exists locally."""

    driver_match = _ODBC_DRIVER_PATTERN.search(raw_connection)
    if not driver_match:
        return raw_connection

    driver_token = driver_match.group(1).strip()
    brace_wrapped = driver_token.startswith("{") and driver_token.endswith("}")
    driver_name = driver_token[1:-1] if brace_wrapped else driver_token

    try:  # pragma: no cover - pyodbc not installed in unit tests
        import pyodbc
    except ModuleNotFoundError:  # pragma: no cover - fallback when pyodbc missing
        return raw_connection

    installed_drivers = pyodbc.drivers()
    lookup = {d.lower(): d for d in installed_drivers}
    normalized_name = driver_name.lower()
    if normalized_name in lookup:
        return raw_connection

    sql_server_drivers = [d for d in installed_drivers if "sql server" in d.lower()]
    replacement = _pick_best_sql_server_driver(sql_server_drivers)
    if replacement is None:
        raise RuntimeError(
            "The configured ODBC driver '%s' is not installed. Install it or update the connection string to use a "
            "driver that exists on this machine." % driver_name
        )

    logger.warning(
        "Configured ODBC driver '%s' is not installed. Falling back to '%s'.",
        driver_name,
        replacement,
    )

    replacement_token = f"{{{replacement}}}" if brace_wrapped else replacement
    return (
        raw_connection[: driver_match.start(1)]
        + replacement_token
        + raw_connection[driver_match.end(1) :]
    )


def _resolve_database_url(raw_url: str) -> str:
    """Return a SQLAlchemy-compatible URL for the configured database."""

    normalized = raw_url.strip()
    if normalized.lower().startswith("driver="):
        # Allow plain ODBC connection strings such as those provided by Azure SQL.
        normalized = _ensure_sql_server_driver(normalized)
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
