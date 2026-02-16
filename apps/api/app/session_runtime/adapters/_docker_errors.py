"""Shared Docker error helpers for session-runtime adapters."""

from __future__ import annotations

import docker.errors


def api_message(exc: docker.errors.APIError) -> str:
    """Extract a human-readable message from a Docker APIError."""
    return exc.explanation if exc.explanation else str(exc)
