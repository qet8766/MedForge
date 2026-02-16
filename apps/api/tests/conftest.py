from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from testcontainers.mysql import MySqlContainer

# Ensure SESSION_SECRET is always available for tests that construct
# Settings() without explicit keyword args (e.g. test_main_lifecycle.py).
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

import app.config as config_module
from app.config import Settings, get_settings
from app.database import get_session, run_migrations
from app.http_contract import (
    apply_legacy_api_deprecation_headers,
    default_problem_responses,
    include_api_routers,
    is_legacy_api_path,
)
from app.models import AuthSession, Competition, Role, User
from app.problem_details import register_problem_exception_handler
from app.routers.auth import router as auth_router
from app.routers.competitions import router
from app.routers.control_plane import router as control_plane_router
from app.security import create_session_token, hash_password, hash_session_token
from app.seed import seed_defaults

MARIADB_IMAGE = "mariadb:11"


@pytest.fixture(scope="session")
def mariadb_url():
    container = MySqlContainer(
        image=MARIADB_IMAGE,
        dbname="medforge_test",
        username="test",
        password="test",
        root_password="roottest",
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(3306)
        yield f"mysql+pymysql://test:test@{host}:{port}/medforge_test"


@pytest.fixture()
def test_settings(tmp_path: Path, mariadb_url: str) -> Settings:
    competitions_dir = tmp_path / "competitions"
    submissions_dir = tmp_path / "submissions"

    (competitions_dir / "titanic-survival").mkdir(parents=True, exist_ok=True)
    (competitions_dir / "rsna-pneumonia-detection").mkdir(parents=True, exist_ok=True)
    (competitions_dir / "cifar-100-classification").mkdir(parents=True, exist_ok=True)

    (competitions_dir / "titanic-survival" / "manifest.json").write_text(
        (
            '{"evaluation_split_version":"titanic-test","scoring_mode":"single_realtime_hidden",'
            '"leaderboard_rule":"best_per_user","evaluation_policy":"canonical_test_first",'
            '"id_column":"PassengerId","target_columns":["Survived"],'
            '"expected_row_count":3}'
        ),
        encoding="utf-8",
    )
    (competitions_dir / "titanic-survival" / "holdout_labels.csv").write_text(
        "PassengerId,Survived\n892,0\n893,1\n894,0\n",
        encoding="utf-8",
    )

    (competitions_dir / "rsna-pneumonia-detection" / "manifest.json").write_text(
        (
            '{"evaluation_split_version":"rsna-test","scoring_mode":"single_realtime_hidden",'
            '"leaderboard_rule":"best_per_user","evaluation_policy":"canonical_test_first",'
            '"id_column":"patientId","target_columns":["x","y","width","height","Target"],'
            '"expected_row_count":4}'
        ),
        encoding="utf-8",
    )
    (competitions_dir / "rsna-pneumonia-detection" / "holdout_labels.csv").write_text(
        "patientId,x,y,width,height,Target\n"
        "p1,100.0,150.0,200.0,250.0,1\n"
        "p1,300.0,400.0,180.0,220.0,1\n"
        "p2,,,,,0\n"
        "p3,50.0,60.0,150.0,160.0,1\n",
        encoding="utf-8",
    )

    (competitions_dir / "cifar-100-classification" / "manifest.json").write_text(
        (
            '{"evaluation_split_version":"cifar100-test","scoring_mode":"single_realtime_hidden",'
            '"leaderboard_rule":"best_per_user","evaluation_policy":"canonical_test_first",'
            '"id_column":"image_id","target_columns":["label"],'
            '"expected_row_count":3}'
        ),
        encoding="utf-8",
    )
    (competitions_dir / "cifar-100-classification" / "holdout_labels.csv").write_text(
        "image_id,label\n0,42\n1,7\n2,99\n",
        encoding="utf-8",
    )

    return Settings(
        database_url=mariadb_url,
        competitions_data_dir=competitions_dir,
        submissions_dir=submissions_dir,
        auto_score_on_submit=True,
        pack_image="medforge-pack-default@sha256:0000000000000000000000000000000000000000000000000000000000000000",
        session_secret="test-session-secret",
        cookie_secure=False,
        cookie_domain="",
        public_sessions_network="medforge-public-sessions",
        workspace_zfs_root="tank/medforge/workspaces",
        session_allocation_max_retries=3,
        session_container_start_timeout_seconds=5,
        session_container_stop_timeout_seconds=5,
        session_runtime_mode="mock",
    )


@pytest.fixture()
def db_engine(test_settings: Settings):
    config_module._SETTINGS = test_settings

    run_migrations(test_settings.database_url)

    engine = create_engine(test_settings.database_url, pool_pre_ping=True, isolation_level="READ COMMITTED")

    with Session(engine) as session:
        seed_defaults(session)
        titanic = session.exec(select(Competition).where(Competition.slug == "titanic-survival")).one()
        titanic.submission_cap_per_day = 1
        session.add(titanic)
        session.commit()

    yield engine

    # Truncate all tables between tests for isolation
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()


@pytest.fixture()
def auth_tokens(db_engine, test_settings: Settings) -> dict[str, str]:
    user_defs = {
        "00000000-0000-0000-0000-000000000011": ("user-a@example.com", Role.USER),
        "00000000-0000-0000-0000-000000000012": ("user-b@example.com", Role.USER),
        "00000000-0000-0000-0000-000000000013": ("admin@example.com", Role.ADMIN),
    }
    now = datetime.now(UTC)
    tokens: dict[str, str] = {}
    with Session(db_engine) as session:
        for user_id, (email, role) in user_defs.items():
            uid = UUID(user_id)
            existing = session.get(User, uid)
            if existing is None:
                session.add(
                    User(
                        id=uid,
                        email=email,
                        password_hash=hash_password("sufficiently-strong"),
                        role=role,
                    )
                )
        session.commit()

        for user_id in user_defs:
            token = create_session_token()
            tokens[user_id] = token
            session.add(
                AuthSession(
                    user_id=UUID(user_id),
                    token_hash=hash_session_token(token, test_settings.session_secret),
                    created_at=now,
                    expires_at=now + timedelta(days=7),
                    last_seen_at=now,
                )
            )
        session.commit()
    return tokens


@pytest.fixture()
def client(test_settings: Settings, db_engine) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        with Session(db_engine) as session:
            yield session

    app = FastAPI(responses=default_problem_responses())

    @app.middleware("http")
    async def request_contract_middleware(request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        if is_legacy_api_path(request.url.path):
            apply_legacy_api_deprecation_headers(response, settings=test_settings)
        return response

    register_problem_exception_handler(app)
    include_api_routers(
        app,
        auth_router=auth_router,
        competitions_router=router,
        control_plane_router=control_plane_router,
    )
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client
