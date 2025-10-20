"""Database configuration and session management."""

from __future__ import annotations

import importlib
import warnings
from collections.abc import Generator
from urllib.parse import quote, urlsplit, urlunsplit

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


settings = get_settings()
database_url = settings.database_url
engine_kwargs: dict[str, object] = {
    "pool_pre_ping": True,
    "pool_size": settings.database_pool_size,
    "max_overflow": settings.database_max_overflow,
    "pool_timeout": settings.database_pool_timeout,
}
if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif settings.database_ssl_mode:
    engine_kwargs["connect_args"] = {"sslmode": settings.database_ssl_mode}

def _percent_encode_credentials(raw_url: str) -> str:
    """Percent-encode username and password components of a database URL."""

    split_url = urlsplit(raw_url)
    netloc = split_url.netloc

    if "@" not in netloc:
        return raw_url

    userinfo, hostinfo = netloc.rsplit("@", 1)
    username, separator, password = userinfo.partition(":")
    encoded_username = quote(username, safe="") if username else ""

    if separator:
        encoded_password = quote(password, safe="") if password else ""
        auth_part = f"{encoded_username}:{encoded_password}"
    else:
        auth_part = encoded_username

    encoded_netloc = f"{auth_part}@{hostinfo}" if auth_part else hostinfo
    return urlunsplit(
        (
            split_url.scheme,
            encoded_netloc,
            split_url.path,
            split_url.query,
            split_url.fragment,
        )
    )


try:
    url = make_url(database_url)
except ValueError:
    database_url = _percent_encode_credentials(database_url)
    url = make_url(database_url)

database_url = url.render_as_string(hide_password=False)

if url.get_backend_name() == "postgresql":
    drivername = url.drivername
    if drivername in {"postgresql", "postgresql+psycopg"}:
        try:
            importlib.import_module("psycopg")
        except ImportError as psycopg_error:
            try:
                importlib.import_module("psycopg2")
            except ImportError as fallback_error:  # pragma: no cover - environment specific
                raise ImportError(
                    "Unable to load the 'psycopg' PostgreSQL driver and no fallback driver "
                    "is available. Install the 'psycopg[binary]' extra or the 'psycopg2-binary' "
                    "package, or update DATABASE_URL to point to an installed driver."
                ) from fallback_error
            else:
                fallback_url = url.set(drivername="postgresql+psycopg2")
                database_url = fallback_url.render_as_string(hide_password=False)
                warnings.warn(
                    "PostgreSQL driver 'psycopg' is unavailable; falling back to 'psycopg2'. "
                    "Install psycopg[binary] or adjust DATABASE_URL to silence this warning.",
                    stacklevel=1,
                )

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database() -> None:
    """Ensure all ORM models have corresponding database tables."""

    importlib.import_module("app.infrastructure.models")
    Base.metadata.create_all(bind=engine, checkfirst=True)


def get_db() -> Generator:
    """Yield a database session and close it afterwards."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


initialize_database()
