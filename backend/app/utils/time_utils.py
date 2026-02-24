"""Time utilities with Europe/Athens local time."""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

try:
    ATHENS_TZ = ZoneInfo("Europe/Athens")
except Exception:
    # Fallback to system local timezone when tzdata is unavailable (Windows)
    ATHENS_TZ = datetime.now().astimezone().tzinfo


def now_athens() -> datetime:
    """Return timezone-aware datetime in Europe/Athens."""
    return datetime.now(ATHENS_TZ)


def now_athens_naive() -> datetime:
    """Return naive datetime representing Europe/Athens local time."""
    return now_athens().replace(tzinfo=None)


def iso_athens() -> str:
    """Return ISO timestamp with Europe/Athens offset."""
    return now_athens().isoformat()


def to_athens(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert a datetime to Europe/Athens tz (assumes Athens if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ATHENS_TZ)
    return dt.astimezone(ATHENS_TZ)


def to_athens_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert a datetime to naive Europe/Athens local time."""
    dt_local = to_athens(dt)
    return dt_local.replace(tzinfo=None) if dt_local else None
