from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from alembic.config import Config
from sqlmodel import Session, create_engine

from alembic import command
from app.config import get_settings


def _normalized_database_url(url: str) -> str:
    if url.startswith("mysql+aiomysql://"):
        return url.replace("mysql+aiomysql://", "mysql+pymysql://", 1)
    return url


def _connect_args(url: str) -> dict[str, object]:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


DATABASE_URL = _normalized_database_url(get_settings().database_url)
engine = create_engine(DATABASE_URL, connect_args=_connect_args(DATABASE_URL), pool_pre_ping=True)


def _alembic_config(database_url: str) -> Config:
    base_dir = Path(__file__).resolve().parents[1]
    config = Config(str(base_dir / "alembic.ini"))
    config.set_main_option("script_location", str(base_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", _normalized_database_url(database_url))
    return config


def run_migrations(database_url: str | None = None) -> None:
    target_url = database_url or get_settings().database_url
    command.upgrade(_alembic_config(target_url), "head")


def init_db() -> None:
    run_migrations(DATABASE_URL)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
