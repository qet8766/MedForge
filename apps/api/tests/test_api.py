from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.models import Competition, Pack, SessionRecord, SessionStatus, Tier, User
from app.session_runtime import MockSessionRuntime, SessionRuntimeError

USER_A = "00000000-0000-0000-0000-000000000011"
USER_B = "00000000-0000-0000-0000-000000000012"


def test_list_competitions(client) -> None:
    response = client.get("/api/competitions")
    assert response.status_code == 200
    payload = response.json()

    slugs = {item["slug"] for item in payload}
    assert "titanic-survival" in slugs
    assert "rsna-pneumonia-detection" in slugs
    assert "cifar-100-classification" in slugs
    assert all(item["competition_tier"] == "PUBLIC" for item in payload)
    assert all(item["scoring_mode"] == "single_realtime_hidden" for item in payload)
    assert all(item["leaderboard_rule"] == "best_per_user" for item in payload)
    assert all(item["evaluation_policy"] == "canonical_test_first" for item in payload)
    assert all(item["competition_spec_version"] == "v1" for item in payload)


def test_competition_detail_status(client) -> None:
    response = client.get("/api/competitions/titanic-survival")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "active"
    assert payload["scoring_mode"] == "single_realtime_hidden"
    assert payload["leaderboard_rule"] == "best_per_user"
    assert payload["evaluation_policy"] == "canonical_test_first"
    assert payload["metric_version"] == "accuracy-v1"
    assert payload["competition_spec_version"] == "v1"


def test_submit_and_score_titanic(client) -> None:
    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["submission"]["score_status"] == "scored"
    assert payload["submission"]["official_score"]["primary_score"] == 1.0
    assert payload["submission"]["official_score"]["metric_version"] == "accuracy-v1"
    assert payload["remaining_today"] == 0

    leaderboard = client.get("/api/competitions/titanic-survival/leaderboard")
    assert leaderboard.status_code == 200
    entries = leaderboard.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["rank"] == 1
    assert entries[0]["primary_score"] == 1.0


def test_submission_cap_enforced(client) -> None:
    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    first = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("preds2.csv", csv_payload, "text/csv")},
    )
    assert second.status_code == 429


def test_invalid_schema_rejected(client) -> None:
    invalid_csv = "PassengerId,WrongColumn\n892,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("invalid.csv", invalid_csv, "text/csv")},
    )
    assert response.status_code == 422
    assert "required columns" in response.json()["detail"]


def test_leaderboard_respects_higher_is_better_flag(client, db_engine) -> None:
    with Session(db_engine) as session:
        competition = session.exec(select(Competition).where(Competition.slug == "titanic-survival")).one()
        competition.higher_is_better = False
        session.add(competition)
        session.commit()

    perfect_csv = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    worst_csv = "PassengerId,Survived\n892,1\n893,0\n894,1\n"

    first = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("high.csv", perfect_csv, "text/csv")},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_B},
        files={"file": ("low.csv", worst_csv, "text/csv")},
    )
    assert second.status_code == 200

    leaderboard = client.get("/api/competitions/titanic-survival/leaderboard")
    assert leaderboard.status_code == 200
    entries = leaderboard.json()["entries"]

    assert len(entries) == 2
    assert entries[0]["user_id"] == USER_B
    assert entries[0]["primary_score"] == 0.0
    assert entries[1]["user_id"] == USER_A
    assert entries[1]["primary_score"] == 1.0


def test_me_requires_auth(client) -> None:
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_supports_legacy_header_when_enabled(client) -> None:
    response = client.get("/api/me", headers={"X-User-Id": USER_A})
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == USER_A
    assert payload["role"] == "user"
    assert payload["email"] is None


def test_submission_rejects_disallowed_origin(client) -> None:
    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_A, "Origin": "https://evil.example"},
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Request origin is not allowed."


def test_admin_score_rejects_disallowed_origin(client, test_settings) -> None:
    client.app.dependency_overrides[get_settings] = lambda: replace(
        test_settings,
        admin_api_token="test-admin-token",
        cookie_secure=False,
        cookie_domain="",
    )

    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    created = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )
    assert created.status_code == 200
    submission_id = created.json()["submission"]["id"]

    disallowed = client.post(
        f"/api/admin/submissions/{submission_id}/score",
        headers={
            "X-User-Id": USER_A,
            "X-Admin-Token": "test-admin-token",
            "Origin": "https://evil.example",
        },
    )
    assert disallowed.status_code == 403
    assert disallowed.json()["detail"] == "Request origin is not allowed."

    allowed = client.post(
        f"/api/admin/submissions/{submission_id}/score",
        headers={
            "X-User-Id": USER_A,
            "X-Admin-Token": "test-admin-token",
            "Origin": "http://localhost:3000",
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["id"] == submission_id


def test_submission_upload_size_limit_returns_structured_422(client, test_settings) -> None:
    client.app.dependency_overrides[get_settings] = lambda: replace(
        test_settings,
        submission_upload_max_bytes=16,
        cookie_secure=False,
        cookie_domain="",
    )

    csv_payload = "PassengerId,Survived\n892,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["body", "file"]
    assert detail[0]["type"] == "value_error.submission_too_large"
    assert detail[0]["ctx"]["max_bytes"] == 16
    assert detail[0]["ctx"]["size_bytes"] > 16


def test_signup_login_logout_cookie_flow(client) -> None:
    signup = client.post(
        "/api/auth/signup",
        json={"email": "dev@example.com", "password": "sufficiently-strong"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert signup.status_code == 201
    user = signup.json()
    assert user["email"] == "dev@example.com"
    assert user["role"] == "user"

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["user_id"] == user["user_id"]

    logout = client.post("/api/auth/logout", headers={"Origin": "http://localhost:3000"})
    assert logout.status_code == 200

    me_after_logout = client.get("/api/me")
    assert me_after_logout.status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"email": "dev@example.com", "password": "sufficiently-strong"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert login.status_code == 200

    me_after_login = client.get("/api/me")
    assert me_after_login.status_code == 200
    assert me_after_login.json()["email"] == "dev@example.com"


def test_legacy_header_disabled_returns_401(client, test_settings) -> None:
    client.app.dependency_overrides[get_settings] = lambda: replace(
        test_settings,
        allow_legacy_header_auth=False,
        cookie_secure=False,
        cookie_domain="",
    )

    response = client.get("/api/me", headers={"X-User-Id": USER_A})
    assert response.status_code == 401


def test_settings_disable_legacy_header_auth_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ALLOW_LEGACY_HEADER_AUTH", raising=False)
    assert Settings().allow_legacy_header_auth is False


def test_session_proxy_requires_auth(client) -> None:
    response = client.get(
        "/api/auth/session-proxy",
        headers={"Host": "s-abc12345.medforge.example.com"},
    )
    assert response.status_code == 401


def test_session_proxy_returns_404_for_invalid_host(client) -> None:
    response = client.get(
        "/api/auth/session-proxy",
        headers={"Host": "invalid.medforge.example.com", "X-User-Id": USER_A},
    )
    assert response.status_code == 404


def test_session_proxy_enforces_owner_and_running(client, db_engine) -> None:
    owner_id = UUID(USER_A)
    other_id = UUID(USER_B)

    with Session(db_engine) as session:
        session.add(User(id=owner_id, email="owner@example.com", password_hash="x"))
        session.add(User(id=other_id, email="other@example.com", password_hash="x"))

        default_pack = session.exec(select(Pack)).first()
        assert default_pack is not None

        session_row = SessionRecord(
            user_id=owner_id,
            tier=Tier.PUBLIC,
            pack_id=default_pack.id,
            status=SessionStatus.RUNNING,
            gpu_id=0,
            gpu_active=1,
            slug="abc12345",
            workspace_zfs="tank/medforge/workspaces/owner/session",
        )
        session.add(session_row)
        session.commit()

    unauthorized = client.get(
        "/api/auth/session-proxy",
        headers={"Host": "s-abc12345.medforge.example.com", "X-User-Id": USER_B},
    )
    assert unauthorized.status_code == 403

    authorized = client.get(
        "/api/auth/session-proxy",
        headers={
            "Host": "s-abc12345.medforge.example.com",
            "X-User-Id": USER_A,
            "X-Upstream": "evil-target:8080",
        },
    )
    assert authorized.status_code == 200
    assert authorized.headers.get("x-upstream") == "mf-session-abc12345:8080"

    with Session(db_engine) as session:
        session_row = session.exec(select(SessionRecord).where(SessionRecord.slug == "abc12345")).one()
        session_row.status = SessionStatus.STOPPED
        session_row.gpu_active = None
        session.add(session_row)
        session.commit()

    stopped = client.get(
        "/api/auth/session-proxy",
        headers={"Host": "s-abc12345.medforge.example.com", "X-User-Id": USER_A},
    )
    assert stopped.status_code == 404


def test_session_create_private_returns_501(client) -> None:
    response = client.post("/api/sessions", json={"tier": "PRIVATE"}, headers={"X-User-Id": USER_A})
    assert response.status_code == 501
    assert "PRIVATE tier" in response.json()["detail"]


def test_session_create_requires_auth(client) -> None:
    response = client.post("/api/sessions", json={"tier": "PUBLIC"})
    assert response.status_code == 401


def test_session_create_public_returns_running(client) -> None:
    response = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert response.status_code == 201
    payload = response.json()
    assert payload["detail"] == "Session started."
    assert payload["session"]["user_id"] == USER_A
    assert payload["session"]["status"] == "running"
    assert payload["session"]["container_id"].startswith("mock-")
    assert payload["session"]["workspace_zfs"].startswith("tank/medforge/workspaces/")


def test_session_create_enforces_user_limit(client) -> None:
    first = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert first.status_code == 201

    second = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert second.status_code == 409
    assert "Concurrent session limit" in second.json()["detail"]


def test_session_create_exhausts_gpu_capacity(client, db_engine) -> None:
    with Session(db_engine) as session:
        session.add(
            User(
                id=UUID(USER_A),
                email="capacity-owner@example.com",
                password_hash="x",
                max_concurrent_sessions=8,
            )
        )
        session.commit()

    statuses = [
        client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A}).status_code
        for _ in range(8)
    ]
    assert statuses.count(201) == 7
    assert statuses.count(409) == 1


def test_session_stop_owner_success_and_idempotent(client) -> None:
    created = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]

    stopped = client.post(f"/api/sessions/{session_id}/stop", headers={"X-User-Id": USER_A})
    assert stopped.status_code == 200
    payload = stopped.json()
    assert payload["detail"] == "Session stopped."
    assert payload["session"]["status"] == "stopped"
    assert payload["session"]["stopped_at"] is not None

    repeated = client.post(f"/api/sessions/{session_id}/stop", headers={"X-User-Id": USER_A})
    assert repeated.status_code == 200
    repeated_payload = repeated.json()
    assert repeated_payload["detail"] == "Session already terminal."
    assert repeated_payload["session"]["status"] == "stopped"


def test_session_stop_forbidden_for_other_user(client) -> None:
    created = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]

    denied = client.post(f"/api/sessions/{session_id}/stop", headers={"X-User-Id": USER_B})
    assert denied.status_code == 403


def test_session_stop_snapshot_failure_marks_error(client, monkeypatch) -> None:
    created = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert created.status_code == 201
    session_id = created.json()["session"]["id"]

    class SnapshotFailureRuntime(MockSessionRuntime):
        def snapshot_workspace(self, workspace_zfs: str, *, snapshot_name: str) -> None:
            _ = (workspace_zfs, snapshot_name)
            raise SessionRuntimeError("simulated snapshot failure")

    monkeypatch.setattr(
        "app.session_lifecycle.get_session_runtime",
        lambda _settings: SnapshotFailureRuntime(),
    )

    response = client.post(f"/api/sessions/{session_id}/stop", headers={"X-User-Id": USER_A})
    assert response.status_code == 200
    payload = response.json()
    assert payload["detail"] == "Session stop failed; marked error."
    assert payload["session"]["status"] == "error"
    assert "snapshot failed" in payload["session"]["error_message"]


def test_session_create_runtime_failure_marks_error(client, db_engine, monkeypatch) -> None:
    class StartFailureRuntime(MockSessionRuntime):
        def start_session_container(self, session_row: SessionRecord, pack: Pack) -> str:
            _ = (session_row, pack)
            raise SessionRuntimeError("simulated container failure")

    monkeypatch.setattr(
        "app.session_lifecycle.get_session_runtime",
        lambda _settings: StartFailureRuntime(),
    )

    response = client.post("/api/sessions", json={"tier": "PUBLIC"}, headers={"X-User-Id": USER_A})
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to start session runtime."

    with Session(db_engine) as session:
        rows = session.exec(select(SessionRecord).where(SessionRecord.user_id == UUID(USER_A))).all()

    assert len(rows) == 1
    assert rows[0].status == SessionStatus.ERROR
    assert rows[0].error_message is not None
    assert "create failed" in rows[0].error_message


def test_submit_and_score_rsna_detection(client) -> None:
    # Submit a perfect-match detection CSV for the RSNA holdout fixture:
    #   p1: two GT boxes (100,150,200,250) and (300,400,180,220)
    #   p2: negative (no boxes)
    #   p3: one GT box (50,60,150,160)
    csv_payload = (
        "patientId,confidence,x,y,width,height\n"
        "p1,0.99,100.0,150.0,200.0,250.0\n"
        "p1,0.95,300.0,400.0,180.0,220.0\n"
        "p2,,,,,\n"
        "p3,0.90,50.0,60.0,150.0,160.0\n"
    )
    response = client.post(
        "/api/competitions/rsna-pneumonia-detection/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submission"]["score_status"] == "scored"
    assert payload["submission"]["official_score"]["primary_score"] == 1.0


def test_submit_and_score_cifar100(client) -> None:
    # Submit a perfect-match classification CSV for the CIFAR-100 holdout fixture:
    #   image_id=0 → label=42, image_id=1 → label=7, image_id=2 → label=99
    csv_payload = "image_id,label\n0,42\n1,7\n2,99\n"
    response = client.post(
        "/api/competitions/cifar-100-classification/submissions",
        headers={"X-User-Id": USER_A},
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submission"]["score_status"] == "scored"
    assert payload["submission"]["official_score"]["primary_score"] == 1.0

    leaderboard = client.get("/api/competitions/cifar-100-classification/leaderboard")
    assert leaderboard.status_code == 200
    entries = leaderboard.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["rank"] == 1
    assert entries[0]["primary_score"] == 1.0
