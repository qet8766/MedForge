"""Shared low-level helpers used across the API codebase."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Session


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


def commit_and_refresh[T](db: Session, instance: T) -> T:
    """Persist instance and return a refreshed copy."""
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def parse_enum_filter[E: StrEnum](filter_str: str | None, enum_class: type[E]) -> list[E]:
    """Parse comma-separated enum values; silently drop invalid ones."""
    if not filter_str:
        return []
    result: list[E] = []
    for raw in filter_str.split(","):
        with contextlib.suppress(ValueError):
            result.append(enum_class(raw.strip()))
    return result
