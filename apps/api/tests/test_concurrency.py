"""MF-101: Concurrent session creation capacity test.

Validates that GPU allocation respects capacity limits:
- 7 GPUs are seeded by default → exactly 7 sessions should succeed
- The 8th request must return a 409 GPU exhaustion error
- All allocated GPU IDs must be unique
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

from sqlmodel import Session, select

from app.models import SessionRecord, SessionStatus, User

USER_A = "00000000-0000-0000-0000-000000000011"


def _auth_headers(auth_tokens: dict[str, str], user_id: str) -> dict[str, str]:
    return {"Cookie": f"medforge_session={auth_tokens[user_id]}"}


def test_8way_parallel_session_create_respects_gpu_capacity(
    client,
    db_engine,
    auth_tokens,
) -> None:
    """8 parallel create requests → 7 succeed (201), 1 fails (409)."""
    with Session(db_engine) as session:
        user = session.get(User, UUID(USER_A))
        assert user is not None
        user.max_concurrent_sessions = 8
        session.add(user)
        session.commit()

    def _create() -> int:
        resp = client.post(
            "/api/v2/external/sessions",
            json={},
            headers=_auth_headers(auth_tokens, USER_A),
        )
        return resp.status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_create) for _ in range(8)]
        codes = [f.result() for f in as_completed(futures)]

    assert codes.count(201) == 7, f"Expected 7 successes, got {codes.count(201)}: {codes}"
    assert codes.count(409) == 1, f"Expected 1 exhaustion, got {codes.count(409)}: {codes}"

    with Session(db_engine) as session:
        rows = session.exec(
            select(SessionRecord)
            .where(SessionRecord.user_id == UUID(USER_A))
            .where(SessionRecord.status.in_([SessionStatus.RUNNING, SessionStatus.STARTING]))  # type: ignore[attr-defined]
        ).all()
        gpu_ids = [r.gpu_id for r in rows]
        assert len(gpu_ids) == 7
        assert len(set(gpu_ids)) == 7, f"GPU IDs not unique: {gpu_ids}"


def test_sequential_session_create_exhausts_gpus(
    client,
    db_engine,
    auth_tokens,
) -> None:
    """Sequential 8 creates → same 7/1 split, deterministic ordering."""
    with Session(db_engine) as session:
        user = session.get(User, UUID(USER_A))
        assert user is not None
        user.max_concurrent_sessions = 8
        session.add(user)
        session.commit()

    statuses = []
    for _ in range(8):
        resp = client.post(
            "/api/v2/external/sessions",
            json={},
            headers=_auth_headers(auth_tokens, USER_A),
        )
        statuses.append(resp.status_code)

    assert statuses.count(201) == 7
    assert statuses.count(409) == 1
    assert statuses[-1] == 409, "Last request should be the one that fails"
