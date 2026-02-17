from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.models import SessionRecord, SessionStatus

from .test_helpers import assert_problem as _assert_problem
from .test_helpers import assert_success as _assert_success

USER_A = "00000000-0000-0000-0000-000000000011"
USER_B = "00000000-0000-0000-0000-000000000012"


def _auth_headers(auth_tokens: dict[str, str], user_id: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Cookie": f"medforge_session={auth_tokens[user_id]}",
    }
    if extra:
        headers.update(extra)
    return headers


def test_sessions_current_requires_auth(client) -> None:
    response = client.get("/api/sessions/current")
    assert response.status_code == 401


def test_sessions_current_returns_null_without_active_session(client, auth_tokens) -> None:
    response = client.get("/api/sessions/current", headers=_auth_headers(auth_tokens, USER_A))
    assert response.status_code == 200
    payload, _ = _assert_success(response, status_code=200)
    assert payload == {"session": None}


def test_sessions_current_returns_requester_session_only(client, auth_tokens) -> None:
    created_a = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    assert created_a.status_code == 201

    created_b = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_B),
    )
    assert created_b.status_code == 201

    response = client.get("/api/sessions/current", headers=_auth_headers(auth_tokens, USER_A))
    payload, _ = _assert_success(response, status_code=200)

    assert payload["session"] is not None
    created_a_data, _ = _assert_success(created_a, status_code=201)
    assert payload["session"]["id"] == created_a_data["session"]["id"]
    assert payload["session"]["user_id"] == USER_A
    assert payload["session"]["status"] == "running"


def test_session_create_rejects_disallowed_origin(client, auth_tokens) -> None:
    response = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A, {"Origin": "https://evil.example.net"}),
    )
    _assert_problem(
        response,
        status_code=403,
        type_suffix="http/403",
    )


def test_session_stop_rejects_disallowed_origin(client, db_engine, auth_tokens) -> None:
    created = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    assert created.status_code == 201
    created_data, _ = _assert_success(created, status_code=201)
    session_id = created_data["session"]["id"]

    denied = client.post(
        f"/api/sessions/{session_id}/stop",
        headers=_auth_headers(auth_tokens, USER_A, {"Origin": "https://evil.example.net"}),
    )
    _assert_problem(
        denied,
        status_code=403,
        type_suffix="http/403",
    )

    with Session(db_engine) as session:
        row = session.exec(select(SessionRecord).where(SessionRecord.id == UUID(session_id))).one()
        assert row.status == SessionStatus.RUNNING
