from __future__ import annotations

import base64
import json

from app.problem_details import ProblemError, normalize_problem_type

_CURSOR_NAMESPACE = "pagination"


def encode_offset_cursor(offset: int) -> str:
    payload = {"offset": offset}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def decode_offset_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise invalid_cursor() from exc

    if not isinstance(payload, dict) or "offset" not in payload:
        raise invalid_cursor()

    offset = payload["offset"]
    if not isinstance(offset, int) or offset < 0:
        raise invalid_cursor()
    return offset


def validate_limit(limit: int, *, max_limit: int = 500) -> int:
    if 1 <= limit <= max_limit:
        return limit
    raise invalid_limit(limit=limit, max_limit=max_limit)


def invalid_cursor() -> ProblemError:
    return ProblemError(
        status_code=400,
        type=normalize_problem_type(f"{_CURSOR_NAMESPACE}/invalid-cursor"),
        title="Invalid Cursor",
        detail="Cursor is invalid or malformed.",
        code="invalid_cursor",
    )


def invalid_limit(*, limit: int, max_limit: int) -> ProblemError:
    return ProblemError(
        status_code=400,
        type=normalize_problem_type(f"{_CURSOR_NAMESPACE}/invalid-limit"),
        title="Invalid Limit",
        detail=f"Limit must be between 1 and {max_limit}. Received {limit}.",
        code="invalid_limit",
    )
