"""Database configuration and session management."""

from __future__ import annotations

import importlib
import warnings
from collections.abc import Generator
from urllib.parse import (
    parse_qsl,
    quote,
    quote_plus,
    unquote_to_bytes,
    urlencode,
    urlsplit,
    urlunsplit,
)

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


settings = get_settings()
database_url = settings.database_url


def _normalize_database_url(raw_url: str) -> str:
    """Convert alternative URL formats (e.g. JDBC) into SQLAlchemy URLs."""

    raw_url = raw_url.strip()
    if raw_url.lower().startswith("jdbc:"):
        jdbc_url = raw_url[5:]
        split_result = urlsplit(jdbc_url)
        query_items = dict(parse_qsl(split_result.query, keep_blank_values=True))
        username = query_items.pop("user", query_items.pop("username", None))
        password = query_items.pop("password", None)
        netloc = split_result.netloc
        if username and "@" not in netloc:
            auth = quote_plus(username)
            if password is not None:
                auth = f"{auth}:{quote_plus(password)}"
            netloc = f"{auth}@{netloc}"
        query = urlencode(query_items, doseq=True)
        jdbc_backend = split_result.scheme or "postgresql+psycopg2"
        if jdbc_backend.startswith("postgresql") and "+" not in jdbc_backend:
            jdbc_backend = "postgresql+psycopg2"
        raw_url = urlunsplit(
            (
                jdbc_backend,
                netloc,
                split_result.path,
                query,
                split_result.fragment,
            )
        )

    return raw_url


database_url = _normalize_database_url(database_url)
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

url = make_url(database_url)


def _encode_if_non_ascii(value: str | None, *, use_plus: bool = False) -> str | None:
    """Percent-encode connection string parts that contain non-ASCII characters.

    On Windows environments it is relatively common to copy connection strings
    from administrative tools that still emit Latin-1 encoded passwords.
    ``psycopg2`` expects UTF-8 encoded credentials and raises ``UnicodeDecodeError``
    when it encounters raw bytes such as ``0xF3`` (``ó``) in the DSN.  To make the
    application resilient we normalise these fragments by decoding any percent
    encoded data, falling back to Latin-1 when UTF-8 decoding fails, and then
    percent-encoding the Unicode string using UTF-8.
    """

    if value is None or value == "":
        return value

    encoder = quote_plus if use_plus else quote

    try:
        contains_non_ascii = any(ord(char) > 127 for char in value)
    except TypeError:  # pragma: no cover - extremely defensive
        return value

    needs_encoding = contains_non_ascii
    decoded_value = value

    if "%" in value:
        try:
            raw_bytes = unquote_to_bytes(value)
        except ValueError:
            raw_bytes = None
        if raw_bytes is not None:
            if any(byte > 127 for byte in raw_bytes):
                needs_encoding = True
            if needs_encoding:
                try:
                    decoded_value = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    decoded_value = raw_bytes.decode("latin-1")

    if not needs_encoding:
        return value

    return encoder(decoded_value, safe="")


username = _encode_if_non_ascii(url.username, use_plus=True)
password = _encode_if_non_ascii(url.password, use_plus=True)
database = _encode_if_non_ascii(url.database)

query_updates: dict[str, str | list[str] | tuple[str, ...]] | None = None
if url.query:
    has_changes = False
    encoded_items: dict[str, str | list[str] | tuple[str, ...]] = {}
    for key, value in url.query.items():
        if isinstance(value, tuple):
            encoded_value = tuple(
                _encode_if_non_ascii(item) or item for item in value
            )
        elif isinstance(value, list):
            encoded_value = [
                _encode_if_non_ascii(item) or item for item in value
            ]
        else:
            encoded_value = _encode_if_non_ascii(value) or value
        encoded_items[key] = encoded_value
        if encoded_value != value:
            has_changes = True
    if has_changes:
        query_updates = encoded_items

updated = False
if username is not url.username:
    url = url.set(username=username)
    updated = True
if password is not url.password:
    url = url.set(password=password)
    updated = True
if database is not url.database:
    url = url.set(database=database)
    updated = True
if query_updates is not None:
    url = url.set(query=query_updates)
    updated = True

if updated:
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
