from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.models import Competition, Pack, SessionRecord, SessionStatus, Tier, User
from app.session_runtime import (
    MockSessionRuntime,
    RuntimeErrorCode,
    SessionRuntimeError,
    SessionStartRequest,
    SessionStartResult,
)

USER_A = "00000000-0000-0000-0000-000000000011"
USER_B = "00000000-0000-0000-0000-000000000012"
ADMIN_USER = "00000000-0000-0000-0000-000000000013"


def _auth_headers(auth_tokens: dict[str, str], user_id: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Cookie": f"medforge_session={auth_tokens[user_id]}",
    }
    if extra:
        headers.update(extra)
    return headers


def _assert_success(response, *, status_code: int) -> tuple[object, dict[str, object]]:
    assert response.status_code == status_code
    payload = response.json()
    assert "data" in payload
    assert "meta" in payload
    meta = payload["meta"]
    assert isinstance(meta["request_id"], str)
    assert meta["request_id"]
    return payload["data"], meta


def _assert_problem(response, *, status_code: int, type_suffix: str) -> dict[str, object]:
    assert response.status_code == status_code
    content_type = response.headers.get("content-type", "")
    assert "application/problem+json" in content_type
    payload = response.json()
    assert payload["status"] == status_code
    assert payload["type"] == f"https://medforge.dev/problems/{type_suffix}"
    assert payload["instance"]
    assert isinstance(payload["title"], str)
    assert isinstance(payload["detail"], str)
    assert isinstance(payload["code"], str)
    assert isinstance(payload["request_id"], str)
    return payload


def test_versioned_routes_match_legacy_routes(client) -> None:
    legacy = client.get("/api/competitions")
    legacy_data, legacy_meta = _assert_success(legacy, status_code=200)
    assert legacy_meta["api_version"] == "v1.0"
    assert legacy.headers.get("deprecation") == "true"
    assert "sunset" in legacy.headers
    assert 'rel="deprecation"' in legacy.headers.get("link", "")

    versioned = client.get("/api/v1/competitions")
    versioned_data, versioned_meta = _assert_success(versioned, status_code=200)
    assert versioned_meta["api_version"] == "v1.0"
    assert "deprecation" not in versioned.headers
    assert "sunset" not in versioned.headers
    assert "link" not in versioned.headers

    assert versioned_data == legacy_data


def test_openapi_problem_responses_use_problem_media_type(client) -> None:
    schema = client.app.openapi()
    login_401 = schema["paths"]["/api/v1/auth/login"]["post"]["responses"]["401"]
    content = login_401["content"]
    assert "application/problem+json" in content
    assert "application/json" not in content
    problem_schema = content["application/problem+json"]["schema"]
    assert isinstance(problem_schema.get("properties"), dict)
    assert "detail" in problem_schema["properties"]


def test_list_competitions(client) -> None:
    response = client.get("/api/competitions")
    data, meta = _assert_success(response, status_code=200)
    _ = meta

    assert isinstance(data, list)
    slugs = {item["slug"] for item in data}
    assert "titanic-survival" in slugs
    assert "rsna-pneumonia-detection" in slugs
    assert "cifar-100-classification" in slugs
    assert all(item["competition_tier"] == "public" for item in data)
    assert all(item["scoring_mode"] == "single_realtime_hidden" for item in data)
    assert all(item["leaderboard_rule"] == "best_per_user" for item in data)
    assert all(item["evaluation_policy"] == "canonical_test_first" for item in data)
    assert all(item["competition_spec_version"] == "v1" for item in data)


def test_competition_detail_status(client) -> None:
    response = client.get("/api/competitions/titanic-survival")
    data, _ = _assert_success(response, status_code=200)
    assert data["status"] == "active"
    assert data["competition_tier"] == "public"
    assert data["scoring_mode"] == "single_realtime_hidden"
    assert data["leaderboard_rule"] == "best_per_user"
    assert data["evaluation_policy"] == "canonical_test_first"
    assert data["metric_version"] == "accuracy-v1"
    assert data["competition_spec_version"] == "v1"


def test_competition_detail_missing_returns_problem_404(client) -> None:
    response = client.get("/api/competitions/does-not-exist")
    payload = _assert_problem(
        response,
        status_code=404,
        type_suffix="competitions/competition-not-found",
    )
    assert "does-not-exist" in payload["detail"]


def test_dataset_missing_returns_problem_404(client) -> None:
    response = client.get("/api/datasets/missing-dataset")
    payload = _assert_problem(
        response,
        status_code=404,
        type_suffix="competitions/dataset-not-found",
    )
    assert "missing-dataset" in payload["detail"]


def test_submit_and_score_titanic(client, auth_tokens) -> None:
    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )

    data, _ = _assert_success(response, status_code=201)
    assert data["submission"]["score_status"] == "scored"
    assert data["submission"]["official_score"]["primary_score"] == 1.0
    assert data["submission"]["official_score"]["metric_version"] == "accuracy-v1"
    assert data["remaining_today"] == 0

    leaderboard = client.get("/api/competitions/titanic-survival/leaderboard")
    leaderboard_data, _ = _assert_success(leaderboard, status_code=200)
    entries = leaderboard_data["entries"]
    assert len(entries) == 1
    assert entries[0]["rank"] == 1
    assert entries[0]["primary_score"] == 1.0


def test_submission_cap_enforced(client, auth_tokens) -> None:
    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    first = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("preds2.csv", csv_payload, "text/csv")},
    )
    payload = _assert_problem(
        second,
        status_code=429,
        type_suffix="competitions/submission-cap-reached",
    )
    assert "Daily submission cap reached" in payload["detail"]


def test_invalid_schema_rejected(client, auth_tokens) -> None:
    invalid_csv = "PassengerId,WrongColumn\n892,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("invalid.csv", invalid_csv, "text/csv")},
    )
    payload = _assert_problem(
        response,
        status_code=422,
        type_suffix="competitions/submission-validation-failed",
    )
    assert "required columns" in payload["detail"]


def test_leaderboard_respects_higher_is_better_flag(client, db_engine, auth_tokens) -> None:
    with Session(db_engine) as session:
        competition = session.exec(select(Competition).where(Competition.slug == "titanic-survival")).one()
        competition.higher_is_better = False
        session.add(competition)
        session.commit()

    perfect_csv = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    worst_csv = "PassengerId,Survived\n892,1\n893,0\n894,1\n"

    first = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("high.csv", perfect_csv, "text/csv")},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_B),
        files={"file": ("low.csv", worst_csv, "text/csv")},
    )
    assert second.status_code == 201

    leaderboard = client.get("/api/competitions/titanic-survival/leaderboard")
    leaderboard_data, _ = _assert_success(leaderboard, status_code=200)
    entries = leaderboard_data["entries"]

    assert len(entries) == 2
    assert entries[0]["user_id"] == USER_B
    assert entries[0]["primary_score"] == 0.0
    assert entries[1]["user_id"] == USER_A
    assert entries[1]["primary_score"] == 1.0


def test_leaderboard_rejects_invalid_pagination(client) -> None:
    invalid_limit = client.get("/api/competitions/titanic-survival/leaderboard?limit=0")
    limit_payload = _assert_problem(
        invalid_limit,
        status_code=400,
        type_suffix="pagination/invalid-limit",
    )
    assert "between 1 and 500" in limit_payload["detail"]

    invalid_cursor = client.get("/api/competitions/titanic-survival/leaderboard?cursor=not-a-cursor")
    cursor_payload = _assert_problem(
        invalid_cursor,
        status_code=400,
        type_suffix="pagination/invalid-cursor",
    )
    assert "Cursor is invalid" in cursor_payload["detail"]


def test_list_my_submissions_returns_desc_created_order(client, auth_tokens) -> None:
    first_csv = "image_id,label\n0,42\n1,7\n2,99\n"
    second_csv = "image_id,label\n0,42\n1,9\n2,99\n"

    first = client.post(
        "/api/competitions/cifar-100-classification/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("first.csv", first_csv, "text/csv")},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/competitions/cifar-100-classification/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("second.csv", second_csv, "text/csv")},
    )
    assert second.status_code == 201

    response = client.get(
        "/api/competitions/cifar-100-classification/submissions/me",
        headers=_auth_headers(auth_tokens, USER_A),
    )
    data, meta = _assert_success(response, status_code=200)
    assert meta["has_more"] is False

    assert len(data) == 2
    assert data[0]["filename"] == "second.csv"
    assert data[1]["filename"] == "first.csv"
    assert data[0]["competition_slug"] == "cifar-100-classification"
    assert data[0]["official_score"] is not None


def test_submission_internal_failure_returns_problem_500(client, monkeypatch, auth_tokens) -> None:
    async def raise_store_failure(
        *,
        settings: Settings,
        competition_slug: str,
        user_id: UUID,
        submission_id: UUID,
        upload: object,
    ) -> None:
        _ = (settings, competition_slug, user_id, submission_id, upload)
        raise RuntimeError("simulated storage failure")

    monkeypatch.setattr(
        "app.routers.competitions.submissions.store_submission_file",
        raise_store_failure,
    )

    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )

    payload = _assert_problem(
        response,
        status_code=500,
        type_suffix="competitions/submission-processing-failed",
    )
    assert payload["detail"] == "An internal error occurred while processing the submission."

    submissions = client.get(
        "/api/competitions/titanic-survival/submissions/me",
        headers=_auth_headers(auth_tokens, USER_A),
    )
    data, _ = _assert_success(submissions, status_code=200)
    assert len(data) == 1
    assert data[0]["score_status"] == "failed"
    assert data[0]["score_error"] == "simulated storage failure"


def test_me_requires_auth(client) -> None:
    response = client.get("/api/me")
    _assert_problem(response, status_code=401, type_suffix="http/401")


def test_me_rejects_legacy_header_auth(client) -> None:
    response = client.get("/api/me", headers={"X-User-Id": USER_A})
    _assert_problem(response, status_code=401, type_suffix="http/401")


def test_submission_rejects_disallowed_origin(client, auth_tokens) -> None:
    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A, {"Origin": "https://evil.example"}),
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )
    payload = _assert_problem(
        response,
        status_code=403,
        type_suffix="competitions/origin-not-allowed",
    )
    assert payload["detail"] == "Request origin is not allowed."


def test_admin_score_rejects_disallowed_origin(client, auth_tokens) -> None:
    csv_payload = "PassengerId,Survived\n892,0\n893,1\n894,0\n"
    created = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )
    assert created.status_code == 201
    submission_id = created.json()["data"]["submission"]["id"]

    disallowed = client.post(
        f"/api/admin/submissions/{submission_id}/score",
        headers=_auth_headers(auth_tokens, ADMIN_USER, {"Origin": "https://evil.example"}),
    )
    payload = _assert_problem(
        disallowed,
        status_code=403,
        type_suffix="competitions/origin-not-allowed",
    )
    assert payload["detail"] == "Request origin is not allowed."

    allowed = client.post(
        f"/api/admin/submissions/{submission_id}/score",
        headers=_auth_headers(auth_tokens, ADMIN_USER, {"Origin": "http://localhost:3000"}),
    )
    data, _ = _assert_success(allowed, status_code=200)
    assert data["id"] == submission_id


def test_admin_score_missing_submission_returns_problem_404(client, auth_tokens) -> None:
    missing_submission_id = "00000000-0000-0000-0000-00000000aaaa"
    response = client.post(
        f"/api/admin/submissions/{missing_submission_id}/score",
        headers=_auth_headers(auth_tokens, ADMIN_USER, {"Origin": "http://localhost:3000"}),
    )
    payload = _assert_problem(
        response,
        status_code=404,
        type_suffix="competitions/submission-not-found",
    )
    assert missing_submission_id in payload["detail"]


def test_admin_score_requires_admin_role(client, auth_tokens) -> None:
    missing_submission_id = "00000000-0000-0000-0000-00000000aaaa"
    response = client.post(
        f"/api/admin/submissions/{missing_submission_id}/score",
        headers=_auth_headers(auth_tokens, USER_A, {"Origin": "http://localhost:3000"}),
    )
    _assert_problem(response, status_code=403, type_suffix="competitions/admin-access-denied")


def test_submission_upload_size_limit_returns_structured_422(client, test_settings, auth_tokens) -> None:
    client.app.dependency_overrides[get_settings] = lambda: replace(
        test_settings,
        submission_upload_max_bytes=16,
        cookie_secure=False,
        cookie_domain="",
    )

    csv_payload = "PassengerId,Survived\n892,0\n"
    response = client.post(
        "/api/competitions/titanic-survival/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )

    payload = _assert_problem(
        response,
        status_code=422,
        type_suffix="competitions/submission-too-large",
    )
    assert "errors" in payload
    errors = payload["errors"]
    assert isinstance(errors, list)
    assert errors[0]["loc"] == ["body", "file"]
    assert errors[0]["type"] == "value_error.submission_too_large"
    assert errors[0]["ctx"]["max_bytes"] == 16
    assert errors[0]["ctx"]["size_bytes"] > 16


def test_signup_login_logout_cookie_flow(client) -> None:
    signup = client.post(
        "/api/auth/signup",
        json={"email": "dev@example.com", "password": "sufficiently-strong"},
        headers={"Origin": "http://localhost:3000"},
    )
    user, _ = _assert_success(signup, status_code=201)
    assert user["email"] == "dev@example.com"
    assert user["role"] == "user"

    me = client.get("/api/me")
    me_data, _ = _assert_success(me, status_code=200)
    assert me_data["user_id"] == user["user_id"]

    logout = client.post("/api/auth/logout", headers={"Origin": "http://localhost:3000"})
    logout_data, _ = _assert_success(logout, status_code=200)
    assert logout_data["message"] == "Signed out."

    me_after_logout = client.get("/api/me")
    _assert_problem(me_after_logout, status_code=401, type_suffix="http/401")

    login = client.post(
        "/api/auth/login",
        json={"email": "dev@example.com", "password": "sufficiently-strong"},
        headers={"Origin": "http://localhost:3000"},
    )
    _assert_success(login, status_code=200)

    me_after_login = client.get("/api/me")
    me_after_login_data, _ = _assert_success(me_after_login, status_code=200)
    assert me_after_login_data["email"] == "dev@example.com"


def test_session_proxy_requires_auth(client) -> None:
    response = client.get(
        "/api/auth/session-proxy",
        headers={"Host": "s-abc12345.medforge.example.com"},
    )
    _assert_problem(response, status_code=401, type_suffix="http/401")


def test_session_proxy_returns_404_for_invalid_host(client, auth_tokens) -> None:
    response = client.get(
        "/api/auth/session-proxy",
        headers=_auth_headers(auth_tokens, USER_A, {"Host": "invalid.medforge.example.com"}),
    )
    _assert_problem(response, status_code=404, type_suffix="http/404")


def test_session_proxy_enforces_owner_and_running(client, db_engine, auth_tokens) -> None:
    owner_id = UUID(USER_A)

    with Session(db_engine) as session:
        default_pack = session.exec(select(Pack)).first()
        assert default_pack is not None

        session_row = SessionRecord(
            user_id=owner_id,
            tier=Tier.PUBLIC,
            pack_id=default_pack.id,
            status=SessionStatus.RUNNING,
            gpu_id=0,
            slug="abc12345",
            workspace_zfs="tank/medforge/workspaces/owner/session",
        )
        session.add(session_row)
        session.commit()

    unauthorized = client.get(
        "/api/auth/session-proxy",
        headers=_auth_headers(auth_tokens, USER_B, {"Host": "s-abc12345.medforge.example.com"}),
    )
    _assert_problem(unauthorized, status_code=403, type_suffix="http/403")

    authorized = client.get(
        "/api/auth/session-proxy",
        headers=_auth_headers(
            auth_tokens,
            USER_A,
            {
                "Host": "s-abc12345.medforge.example.com",
                "X-Upstream": "evil-target:8080",
            },
        ),
    )
    assert authorized.status_code == 200
    assert authorized.headers.get("x-upstream") == "mf-session-abc12345:8080"

    with Session(db_engine) as session:
        session_row = session.exec(select(SessionRecord).where(SessionRecord.slug == "abc12345")).one()
        session_row.status = SessionStatus.STOPPED
        session.add(session_row)
        session.commit()

    stopped = client.get(
        "/api/auth/session-proxy",
        headers=_auth_headers(auth_tokens, USER_A, {"Host": "s-abc12345.medforge.example.com"}),
    )
    _assert_problem(stopped, status_code=404, type_suffix="http/404")


def test_session_create_private_returns_501(client, auth_tokens) -> None:
    response = client.post(
        "/api/sessions",
        json={"tier": "private"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    payload = _assert_problem(response, status_code=501, type_suffix="http/501")
    assert "private tier" in payload["detail"]


def test_session_create_uppercase_tier_rejected(client, auth_tokens) -> None:
    response = client.post(
        "/api/sessions",
        json={"tier": "PUBLIC"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    _assert_problem(response, status_code=422, type_suffix="validation/request")


def test_session_create_requires_auth(client) -> None:
    response = client.post("/api/sessions", json={"tier": "public"})
    _assert_problem(response, status_code=401, type_suffix="http/401")


def test_session_create_public_returns_running(client, auth_tokens) -> None:
    response = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    data, _ = _assert_success(response, status_code=201)
    assert data["message"] == "Session started."
    assert data["session"]["user_id"] == USER_A
    assert data["session"]["status"] == "running"
    assert data["session"]["container_id"].startswith("mock-")
    assert data["session"]["workspace_zfs"].startswith("tank/medforge/workspaces/")


def test_session_create_enforces_user_limit(client, auth_tokens) -> None:
    first = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    assert first.status_code == 201

    second = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    payload = _assert_problem(second, status_code=409, type_suffix="http/409")
    assert "Concurrent session limit" in payload["detail"]


def test_session_create_exhausts_gpu_capacity(client, db_engine, auth_tokens) -> None:
    with Session(db_engine) as session:
        user = session.get(User, UUID(USER_A))
        assert user is not None
        user.max_concurrent_sessions = 8
        session.add(user)
        session.commit()

    statuses = [
        client.post(
            "/api/sessions",
            json={"tier": "public"},
            headers=_auth_headers(auth_tokens, USER_A),
        ).status_code
        for _ in range(8)
    ]
    assert statuses.count(201) == 7
    assert statuses.count(409) == 1


def test_session_stop_owner_marks_stopping_and_is_idempotent(client, auth_tokens) -> None:
    created = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    assert created.status_code == 201
    session_id = created.json()["data"]["session"]["id"]

    stopped = client.post(
        f"/api/sessions/{session_id}/stop",
        headers=_auth_headers(auth_tokens, USER_A),
    )
    stopped_data, _ = _assert_success(stopped, status_code=202)
    assert stopped_data["message"] == "Session stop requested."

    repeated = client.post(
        f"/api/sessions/{session_id}/stop",
        headers=_auth_headers(auth_tokens, USER_A),
    )
    repeated_data, _ = _assert_success(repeated, status_code=202)
    assert repeated_data["message"] == "Session stop requested."

    current = client.get("/api/sessions/current", headers=_auth_headers(auth_tokens, USER_A))
    current_data, _ = _assert_success(current, status_code=200)
    assert current_data["session"] is not None
    assert current_data["session"]["status"] == "stopping"


def test_session_stop_forbidden_for_other_user(client, auth_tokens) -> None:
    created = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    assert created.status_code == 201
    session_id = created.json()["data"]["session"]["id"]

    denied = client.post(
        f"/api/sessions/{session_id}/stop",
        headers=_auth_headers(auth_tokens, USER_B),
    )
    _assert_problem(denied, status_code=403, type_suffix="http/403")


def test_session_stop_terminal_row_returns_current_state(client, db_engine, auth_tokens) -> None:
    created = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    assert created.status_code == 201
    session_id = created.json()["data"]["session"]["id"]
    with Session(db_engine) as session:
        row = session.exec(select(SessionRecord).where(SessionRecord.id == UUID(session_id))).one()
        row.status = SessionStatus.STOPPED
        row.stopped_at = row.created_at
        session.add(row)
        session.commit()

    response = client.post(
        f"/api/sessions/{session_id}/stop",
        headers=_auth_headers(auth_tokens, USER_A),
    )
    payload, _ = _assert_success(response, status_code=202)
    assert payload["message"] == "Session already terminal."


def test_session_create_runtime_failure_marks_error(client, db_engine, monkeypatch, auth_tokens) -> None:
    class StartFailureRuntime(MockSessionRuntime):
        def start_session(self, request: SessionStartRequest) -> SessionStartResult:
            _ = request
            raise SessionRuntimeError(
                code=RuntimeErrorCode.CONTAINER_START_FAILED,
                operation="test.start_session",
                message="simulated container failure",
            )

    monkeypatch.setattr(
        "app.session_lifecycle.get_session_runtime",
        lambda _settings: StartFailureRuntime(),
    )

    response = client.post(
        "/api/sessions",
        json={"tier": "public"},
        headers=_auth_headers(auth_tokens, USER_A),
    )
    payload = _assert_problem(response, status_code=500, type_suffix="http/500")
    assert payload["detail"] == "Failed to start session runtime."

    with Session(db_engine) as session:
        rows = session.exec(select(SessionRecord).where(SessionRecord.user_id == UUID(USER_A))).all()

    assert len(rows) == 1
    assert rows[0].status == SessionStatus.ERROR
    assert rows[0].error_message is not None
    assert "create failed" in rows[0].error_message


def test_submit_and_score_rsna_detection(client, auth_tokens) -> None:
    csv_payload = (
        "patientId,confidence,x,y,width,height\n"
        "p1,0.99,100.0,150.0,200.0,250.0\n"
        "p1,0.95,300.0,400.0,180.0,220.0\n"
        "p2,,,,,\n"
        "p3,0.90,50.0,60.0,150.0,160.0\n"
    )
    response = client.post(
        "/api/competitions/rsna-pneumonia-detection/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )
    data, _ = _assert_success(response, status_code=201)
    assert data["submission"]["score_status"] == "scored"
    assert data["submission"]["official_score"]["primary_score"] == 1.0


def test_submit_and_score_cifar100(client, auth_tokens) -> None:
    csv_payload = "image_id,label\n0,42\n1,7\n2,99\n"
    response = client.post(
        "/api/competitions/cifar-100-classification/submissions",
        headers=_auth_headers(auth_tokens, USER_A),
        files={"file": ("preds.csv", csv_payload, "text/csv")},
    )

    data, _ = _assert_success(response, status_code=201)
    assert data["submission"]["score_status"] == "scored"
    assert data["submission"]["official_score"]["primary_score"] == 1.0

    leaderboard = client.get("/api/competitions/cifar-100-classification/leaderboard")
    leaderboard_data, _ = _assert_success(leaderboard, status_code=200)
    entries = leaderboard_data["entries"]
    assert len(entries) == 1
    assert entries[0]["rank"] == 1
    assert entries[0]["primary_score"] == 1.0
