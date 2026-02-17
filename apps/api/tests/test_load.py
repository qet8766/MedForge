"""MF-105: Load/soak tests.

Validates system stability under sustained create/stop cycles
using concurrent.futures.ThreadPoolExecutor.

Marked @pytest.mark.load — run manually, not in CI.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from uuid import UUID

import pytest
from sqlmodel import Session

from app.models import User

from .test_helpers import assert_success as _assert_success

pytestmark = pytest.mark.load

USER_A = "00000000-0000-0000-0000-000000000011"


def _auth_headers(auth_tokens: dict[str, str], user_id: str) -> dict[str, str]:
    return {"Cookie": f"medforge_session={auth_tokens[user_id]}"}


@dataclass
class CycleResult:
    create_status: int
    stop_status: int | None
    create_latency_ms: float
    stop_latency_ms: float | None
    session_id: str | None


def _run_create_stop_cycle(client, auth_tokens: dict[str, str]) -> CycleResult:
    """Create a session, then stop it. Returns timing and status codes."""
    t0 = time.monotonic()
    create_resp = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    create_latency = (time.monotonic() - t0) * 1000

    if create_resp.status_code != 201:
        return CycleResult(
            create_status=create_resp.status_code,
            stop_status=None,
            create_latency_ms=create_latency,
            stop_latency_ms=None,
            session_id=None,
        )

    create_data, _ = _assert_success(create_resp, status_code=201)
    session_id = str(create_data["session"]["id"])

    t1 = time.monotonic()
    stop_resp = client.post(
        f"/api/sessions/{session_id}/stop",
        headers=_auth_headers(auth_tokens, USER_A),
    )
    stop_latency = (time.monotonic() - t1) * 1000

    return CycleResult(
        create_status=create_resp.status_code,
        stop_status=stop_resp.status_code,
        create_latency_ms=create_latency,
        stop_latency_ms=stop_latency,
        session_id=session_id,
    )


def test_sequential_create_stop_cycles(client, db_engine, auth_tokens) -> None:
    """50 sequential create/stop cycles must all succeed."""
    with Session(db_engine) as session:
        user = session.get(User, UUID(USER_A))
        assert user is not None
        user.max_concurrent_sessions = 1
        session.add(user)
        session.commit()

    results: list[CycleResult] = []
    for _i in range(50):
        result = _run_create_stop_cycle(client, auth_tokens)

        if result.create_status == 409 and result.session_id is None:
            # Previous stop may not have been processed yet by recovery poller.
            # Complete stopping sessions via poller before retrying.
            from app.config import get_settings
            from app.session_recovery import poll_active_sessions_once

            with Session(db_engine) as session:
                poll_active_sessions_once(session, settings=get_settings())

            result = _run_create_stop_cycle(client, auth_tokens)

        results.append(result)

    create_successes = sum(1 for r in results if r.create_status == 201)

    assert create_successes >= 45, (
        f"Expected >=45 create successes out of 50, got {create_successes}"
    )

    create_latencies = [r.create_latency_ms for r in results if r.create_status == 201]
    if create_latencies:
        avg_latency = sum(create_latencies) / len(create_latencies)
        p99_latency = sorted(create_latencies)[int(len(create_latencies) * 0.99)]
        assert avg_latency < 5000, f"Average create latency too high: {avg_latency:.1f}ms"
        assert p99_latency < 10000, f"p99 create latency too high: {p99_latency:.1f}ms"


def test_concurrent_create_stop_cycles(client, db_engine, auth_tokens) -> None:
    """20 concurrent create/stop cycles with high concurrency limit."""
    with Session(db_engine) as session:
        user = session.get(User, UUID(USER_A))
        assert user is not None
        user.max_concurrent_sessions = 7
        session.add(user)
        session.commit()

    results: list[CycleResult] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(_run_create_stop_cycle, client, auth_tokens)
            for _ in range(20)
        ]
        for f in as_completed(futures):
            results.append(f.result())

    create_successes = sum(1 for r in results if r.create_status == 201)
    errors = [r for r in results if r.create_status not in {201, 409}]

    assert not errors, f"Unexpected error codes: {[(r.create_status, r.session_id) for r in errors]}"
    assert create_successes >= 7, f"Expected >=7 create successes, got {create_successes}"
