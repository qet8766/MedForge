from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def _normalized_database_url() -> str:
    url = get_settings().database_url
    if url.startswith("mysql+aiomysql://"):
        return url.replace("mysql+aiomysql://", "mysql+pymysql://", 1)
    return url


def _connect_args(url: str) -> dict[str, object]:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


DATABASE_URL = _normalized_database_url()
engine = create_engine(DATABASE_URL, connect_args=_connect_args(DATABASE_URL), pool_pre_ping=True)
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []

    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        current.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(current).strip()
            if statement.endswith(";"):
                statement = statement[:-1]
            if statement:
                statements.append(statement)
            current = []

    trailing = "\n".join(current).strip()
    if trailing:
        statements.append(trailing)

    return statements


def _run_migrations() -> None:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at DATETIME(6) NOT NULL
                )
                """
            )
        )
        applied = {
            row[0]
            for row in connection.execute(text("SELECT version FROM schema_migrations")).all()
        }

        for migration_path in migration_files:
            version = migration_path.name
            if version in applied:
                continue

            sql_script = migration_path.read_text(encoding="utf-8")
            for statement in _split_sql_statements(sql_script):
                connection.execute(text(statement))

            connection.execute(
                text(
                    """
                    INSERT INTO schema_migrations (version, applied_at)
                    VALUES (:version, :applied_at)
                    """
                ),
                {
                    "version": version,
                    "applied_at": datetime.now(UTC).replace(tzinfo=None),
                },
            )


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite"):
        SQLModel.metadata.create_all(engine)
        return
    _run_migrations()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
