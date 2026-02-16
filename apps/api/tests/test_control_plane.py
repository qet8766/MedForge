from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.models import SessionRecord, SessionStatus

USER_A = "00000000-0000-0000-0000-000000000011"
USER_B = "00000000-0000-0000-0000-000000000012"


def test_sessions_current_requires_auth(client) -> None:
    response = client.get("/api/sessions/current")
    assert response.status_code == 401


def test_sessions_current_returns_null_without_active_session(client) -> None:
    response = client.get("/api/sessions/current", headers={"X-User-Id": USER_A})
    assert response.status_code == 200
    assert response.json() == {"session": None}


def test_sessions_current_returns_requester_session_only(client) -> None:
    created_a = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert created_a.status_code == 201

    created_b = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_B})
    assert created_b.status_code == 201

    response = client.get("/api/sessions/current", headers={"X-User-Id": USER_A})
    assert response.status_code == 200
    payload = response.json()

    assert payload["session"] is not None
    assert payload["session"]["id"] == created_a.json()["session"]["id"]
    assert payload["session"]["user_id"] == USER_A
    assert payload["session"]["status"] == "running"


def test_session_create_rejects_disallowed_origin(client) -> None:
    response = client.post(
        "/api/sessions",
        json={"tier": "PUBLIC"},
        headers={"X-User-Id": USER_A, "Origin": "https://evil.example.net"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Request origin is not allowed."


def test_session_stop_rejects_disallowed_origin(client, db_engine) -> None:
    created = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]

    denied = client.post(
        f"/api/sessions/{session_id}/stop",
        headers={"X-User-Id": USER_A, "Origin": "https://evil.example.net"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Request origin is not allowed."

    with Session(db_engine) as session:
        row = session.exec(select(SessionRecord).where(SessionRecord.id == UUID(session_id))).one()
        assert row.status == SessionStatus.RUNNING
