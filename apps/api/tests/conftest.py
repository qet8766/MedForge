from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import Settings, get_settings
from app.database import get_session
from app.models import Competition
from app.routers.auth import router as auth_router
from app.routers.competitions import router
from app.routers.control_plane import router as control_plane_router
from app.seed import seed_defaults


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    competitions_dir = tmp_path / "competitions"
    submissions_dir = tmp_path / "submissions"

    (competitions_dir / "titanic-survival").mkdir(parents=True, exist_ok=True)
    (competitions_dir / "rsna-pneumonia-detection").mkdir(parents=True, exist_ok=True)

    (competitions_dir / "titanic-survival" / "manifest.json").write_text(
        '{"evaluation_split_version":"titanic-test"}', encoding="utf-8"
    )
    (competitions_dir / "titanic-survival" / "holdout_labels.csv").write_text(
        "PassengerId,Survived\n892,0\n893,1\n894,0\n",
        encoding="utf-8",
    )

    (competitions_dir / "rsna-pneumonia-detection" / "manifest.json").write_text(
        '{"evaluation_split_version":"rsna-test"}', encoding="utf-8"
    )
    (competitions_dir / "rsna-pneumonia-detection" / "holdout_labels.csv").write_text(
        "patientId,Target\np1,1\np2,0\np3,1\n",
        encoding="utf-8",
    )

    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        competitions_data_dir=competitions_dir,
        submissions_dir=submissions_dir,
        auto_score_on_submit=True,
        allow_legacy_header_auth=True,
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
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        seed_defaults(session)
        titanic = session.exec(select(Competition).where(Competition.slug == "titanic-survival")).one()
        titanic.submission_cap_per_day = 1
        session.add(titanic)
        session.commit()

    return engine


@pytest.fixture()
def client(test_settings: Settings, db_engine) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        with Session(db_engine) as session:
            yield session

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(router)
    app.include_router(control_plane_router)
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as test_client:
        yield test_client
