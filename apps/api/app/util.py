"""Shared low-level helpers used across the API codebase."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Ensure *value* carries UTC tzinfo, attaching it if naive."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
