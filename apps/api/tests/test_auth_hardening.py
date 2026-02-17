"""MF-101 / MF-104: Auth hardening tests.

Validates:
- X-Upstream spoof rejection
- Origin validation matrix
- Rate limit 429 responses on auth endpoints
- Session fixation (logout → reuse token → 401)
- Idle TTL expiry
- Max TTL expiry
"""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlmodel import Session, select

from app.config import get_settings
from app.models import AuthSession
from app.security import hash_session_token

from .test_helpers import assert_problem as _assert_problem

USER_A = "00000000-0000-0000-0000-000000000011"
USER_B = "00000000-0000-0000-0000-000000000012"
ALLOWED_ORIGIN = "https://medforge.example.com"
ALLOWED_API_ORIGIN = "https://api.medforge.example.com"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the auth rate limiter singleton between tests."""
    import app.rate_limit as rl
    rl._auth_limiter._buckets.clear()
    yield
    rl._auth_limiter._buckets.clear()


def _auth_headers(auth_tokens: dict[str, str], user_id: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Cookie": f"medforge_session={auth_tokens[user_id]}"}
    if extra:
        headers.update(extra)
    return headers


# ── X-Upstream spoof rejection ──────────────────────────────────────


def test_session_proxy_strips_spoofed_x_upstream(client, db_engine, auth_tokens) -> None:
    """Owner request with spoofed X-Upstream header → overwritten by server."""
    from app.models import Pack, SessionRecord, SessionStatus, Exposure

    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        row = SessionRecord(
            user_id=UUID(USER_A),
            exposure=Exposure.EXTERNAL,
            pack_id=pack.id,
            status=SessionStatus.RUNNING,
            gpu_id=0,
            slug="spoof123",
            workspace_zfs="tank/medforge/workspaces/test/spoof",
        )
        session.add(row)
        session.commit()

    response = client.get(
        "/api/v2/auth/session-proxy",
        headers=_auth_headers(
            auth_tokens,
            USER_A,
            {
                "Host": "s-spoof123.external.medforge.example.com",
                "X-Upstream": "evil-target:9999",
            },
        ),
    )
    assert response.status_code == 200
    assert response.headers["x-upstream"] == "mf-session-spoof123:8080"
    assert "evil" not in response.headers["x-upstream"]


# ── Origin validation matrix ────────────────────────────────────────


def test_origin_matrix_allowed_origins(client, auth_tokens) -> None:
    """Known-good origins must be accepted on protected endpoints."""
    good_origins = [
        ALLOWED_ORIGIN,
        ALLOWED_API_ORIGIN,
        "https://s-origintest.external.medforge.example.com",
    ]
    for origin in good_origins:
        resp = client.post(
            "/api/v2/auth/signup",
            json={"email": f"origin-test-{origin.replace(':', '-').replace('/', '-')}@example.com", "password": "sufficiently-strong"},
            headers={"Origin": origin},
        )
        assert resp.status_code in {201, 409}, f"Origin {origin} rejected unexpectedly: {resp.status_code}"


def test_origin_matrix_rejected_origins(client, auth_tokens) -> None:
    """Disallowed origins must be rejected with 403."""
    bad_origins = [
        "https://evil.example.com",
        "https://attacker.example.com",
        "http://malicious.medforge-fake.com",
    ]
    for origin in bad_origins:
        resp = client.post(
            "/api/v2/external/sessions",
            json={},
            headers=_auth_headers(auth_tokens, USER_A, {"Origin": origin}),
        )
        assert resp.status_code == 403, f"Origin {origin} not rejected: {resp.status_code}"


# ── Rate limit 429 responses ────────────────────────────────────────


def test_auth_signup_rate_limit_429(client) -> None:
    """Rapid signup requests → 429 after exceeding rate limit."""
    for i in range(10):
        client.post(
            "/api/v2/auth/signup",
            json={"email": f"ratelimit-{i}@example.com", "password": "sufficiently-strong"},
            headers={"Origin": ALLOWED_ORIGIN},
        )

    response = client.post(
        "/api/v2/auth/signup",
        json={"email": "ratelimit-overflow@example.com", "password": "sufficiently-strong"},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    payload = _assert_problem(
        response,
        status_code=429,
        type_suffix="rate-limit/exceeded",
    )
    assert payload["code"] == "rate_limit_exceeded"
    assert "Retry-After" in response.headers


def test_auth_login_rate_limit_429(client) -> None:
    """Rapid login requests → 429 after exceeding rate limit."""
    for i in range(10):
        client.post(
            "/api/v2/auth/login",
            json={"email": f"ratelimit-login-{i}@example.com", "password": "wrong"},
            headers={"Origin": ALLOWED_ORIGIN},
        )

    response = client.post(
        "/api/v2/auth/login",
        json={"email": "ratelimit-login-overflow@example.com", "password": "wrong"},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    payload = _assert_problem(
        response,
        status_code=429,
        type_suffix="rate-limit/exceeded",
    )
    assert payload["code"] == "rate_limit_exceeded"


# ── Session fixation ────────────────────────────────────────────────


def test_logout_invalidates_token(client) -> None:
    """After logout, the old token must return 401."""
    signup = client.post(
        "/api/v2/auth/signup",
        json={"email": "fixation-test@example.com", "password": "sufficiently-strong"},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert signup.status_code == 201
    cookie_header = signup.headers.get("set-cookie", "")
    assert "medforge_session=" in cookie_header

    token = None
    for part in cookie_header.split(";"):
        if "medforge_session=" in part:
            token = part.split("=", 1)[1].strip()
            break
    assert token is not None

    logout = client.post("/api/v2/auth/logout", headers={"Origin": ALLOWED_ORIGIN})
    assert logout.status_code == 200

    me = client.get("/api/v2/me", headers={"Cookie": f"medforge_session={token}"})
    assert me.status_code == 401


# ── Idle TTL expiry ─────────────────────────────────────────────────


def test_idle_ttl_expires_session(client, db_engine, test_settings, auth_tokens) -> None:
    """Session idle beyond AUTH_IDLE_TTL_SECONDS → 401."""
    short_ttl_settings = replace(
        test_settings,
        auth_idle_ttl_seconds=1,
        cookie_secure=False,
        cookie_domain="",
    )
    client.app.dependency_overrides[get_settings] = lambda: short_ttl_settings

    with Session(db_engine) as session:
        token_hash = hash_session_token(auth_tokens[USER_A], test_settings.session_secret)
        auth_session = session.exec(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        ).first()
        assert auth_session is not None
        past = datetime.now(UTC) - timedelta(seconds=10)
        auth_session.expires_at = past
        auth_session.last_seen_at = past
        session.add(auth_session)
        session.commit()

    me = client.get("/api/v2/me", headers=_auth_headers(auth_tokens, USER_A))
    assert me.status_code == 401


# ── Max TTL expiry ──────────────────────────────────────────────────


def test_max_ttl_expires_session(client, db_engine, test_settings, auth_tokens) -> None:
    """Session beyond AUTH_MAX_TTL_SECONDS → 401 even if recently active."""
    short_max_settings = replace(
        test_settings,
        auth_max_ttl_seconds=1,
        auth_idle_ttl_seconds=604800,
        cookie_secure=False,
        cookie_domain="",
    )
    client.app.dependency_overrides[get_settings] = lambda: short_max_settings

    with Session(db_engine) as session:
        token_hash = hash_session_token(auth_tokens[USER_A], test_settings.session_secret)
        auth_session = session.exec(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        ).first()
        assert auth_session is not None
        old_creation = datetime.now(UTC) - timedelta(seconds=10)
        auth_session.created_at = old_creation
        auth_session.expires_at = datetime.now(UTC) + timedelta(days=7)
        auth_session.last_seen_at = datetime.now(UTC)
        session.add(auth_session)
        session.commit()

    me = client.get("/api/v2/me", headers=_auth_headers(auth_tokens, USER_A))
    assert me.status_code == 401
