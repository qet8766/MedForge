from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import Request

from app.problem_details import ProblemError, normalize_problem_type


@dataclass
class _Bucket:
    tokens: list[float] = field(default_factory=list)


class RateLimiter:
    """In-memory sliding-window rate limiter keyed by client IP."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = defaultdict(_Bucket)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self._window_seconds
        with self._lock:
            bucket = self._buckets[key]
            bucket.tokens = [t for t in bucket.tokens if t > cutoff]
            if len(bucket.tokens) >= self._max_requests:
                raise ProblemError(
                    status_code=429,
                    type=normalize_problem_type("rate-limit/exceeded"),
                    title="Too Many Requests",
                    detail="Rate limit exceeded. Try again later.",
                    code="rate_limit_exceeded",
                    headers={"Retry-After": str(self._window_seconds)},
                )
            bucket.tokens.append(now)


# Singleton: 10 requests per 60 seconds.
_auth_limiter = RateLimiter(max_requests=10, window_seconds=60)


def require_auth_rate_limit(request: Request) -> None:
    """FastAPI dependency that enforces rate limiting on auth endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    _auth_limiter.check(client_ip)
