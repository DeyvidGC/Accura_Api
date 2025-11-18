"""Helpers for working with timezone-aware datetimes."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone, tzinfo
from functools import lru_cache
from typing import Final

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import get_settings

_DEFAULT_TIMEZONE: Final[str] = "America/Bogota"
_OFFSET_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?:UTC|GMT)(?P<sign>[+-])(?P<hours>\d{1,2})(?::?(?P<minutes>\d{2}))?$",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def get_app_timezone() -> tzinfo:
    """Return the configured application timezone.

    The timezone is resolved using the ``APP_TIMEZONE`` environment variable (via
    the ``Settings`` dataclass). If the provided value cannot be resolved, the
    default ``America/Bogota`` timezone is used as a fallback.
    """

    settings = get_settings()
    tz_name = (settings.app_timezone or "").strip() or _DEFAULT_TIMEZONE
    return _resolve_timezone(tz_name)


def now_in_app_timezone() -> datetime:
    """Return the current time localized to the configured timezone."""

    return datetime.now(tz=get_app_timezone())


def now_in_app_naive_datetime() -> datetime:
    """Return the current localized time without attaching ``tzinfo``."""

    localized = ensure_app_naive_datetime(now_in_app_timezone())
    if localized is None:  # pragma: no cover - defensive guard
        msg = "Failed to compute the application naive datetime"
        raise RuntimeError(msg)
    return localized


def ensure_app_timezone(value: datetime | None) -> datetime | None:
    """Normalize ``value`` so it is expressed in the configured timezone."""

    if value is None:
        return None

    tz = get_app_timezone()
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def ensure_app_naive_datetime(value: datetime | None) -> datetime | None:
    """Return ``value`` localized to the app timezone but without ``tzinfo``.

    SQL Server ``DATETIME`` columns do not accept timezone-aware values. This helper
    allows us to keep working with aware datetimes in the domain layer while storing
    the localized (naive) representation in the database.
    """

    localized = ensure_app_timezone(value)
    if localized is None:
        return None
    return localized.replace(tzinfo=None)


def _resolve_timezone(tz_name: str) -> tzinfo:
    """Resolve ``tz_name`` into a ``timezone`` instance."""

    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        match = _OFFSET_PATTERN.match(tz_name)
        if match:
            sign = -1 if match.group("sign") == "-" else 1
            hours = int(match.group("hours"))
            minutes = int(match.group("minutes") or 0)
            offset = timedelta(hours=hours, minutes=minutes)
            return timezone(sign * offset)
    return ZoneInfo(_DEFAULT_TIMEZONE)
