from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Column, Index, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class Tier(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


class SessionStatus(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class PackTier(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    BOTH = "BOTH"


class CompetitionTier(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class CompetitionStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ScoreStatus(StrEnum):
    QUEUED = "queued"
    SCORING = "scoring"
    SCORED = "scored"
    FAILED = "failed"


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("max_concurrent_sessions > 0", name="ck_users_max_sessions_positive"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=320)
    password_hash: str = Field(max_length=255)
    role: Role = Field(default=Role.USER, sa_column=Column(SAEnum(Role, name="role"), nullable=False))
    max_concurrent_sessions: int = Field(default=1)
    created_at: datetime = Field(default_factory=utcnow)


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True, unique=True, max_length=128)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(index=True)
    revoked_at: datetime | None = Field(default=None)
    last_seen_at: datetime | None = Field(default=None)
    ip: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=512)


class Pack(SQLModel, table=True):
    __tablename__ = "packs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=120)
    tier: PackTier = Field(sa_column=Column(SAEnum(PackTier, name="pack_tier"), nullable=False))
    image_ref: str = Field(max_length=255)
    image_digest: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=utcnow)
    deprecated_at: datetime | None = Field(default=None)


class GpuDevice(SQLModel, table=True):
    __tablename__ = "gpu_devices"

    id: int = Field(primary_key=True)
    enabled: bool = Field(default=True)


class SessionRecord(SQLModel, table=True):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("gpu_id", "gpu_active", name="uq_sessions_gpu_active"),
        Index("ix_sessions_user_status", "user_id", "status"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    tier: Tier = Field(sa_column=Column(SAEnum(Tier, name="tier"), nullable=False))
    pack_id: uuid.UUID = Field(foreign_key="packs.id", index=True)
    status: SessionStatus = Field(sa_column=Column(SAEnum(SessionStatus, name="session_status"), nullable=False))
    container_id: str | None = Field(default=None, max_length=128)
    gpu_id: int = Field(foreign_key="gpu_devices.id", index=True)
    gpu_active: int | None = Field(default=None)
    slug: str = Field(index=True, unique=True, min_length=8, max_length=8)
    workspace_zfs: str = Field(unique=True, max_length=255)
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = Field(default=None)
    stopped_at: datetime | None = Field(default=None)
    error_message: str | None = Field(default=None, max_length=2000)


class Dataset(SQLModel, table=True):
    __tablename__ = "datasets"
    __table_args__ = (CheckConstraint("bytes >= 0", name="ck_datasets_bytes_nonnegative"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(index=True, unique=True, max_length=120)
    title: str = Field(max_length=255)
    source: str = Field(max_length=120)
    license: str = Field(max_length=255)
    storage_path: str = Field(max_length=512)
    bytes: int = Field(default=0)
    checksum: str = Field(max_length=128)
    created_at: datetime = Field(default_factory=utcnow)


class Competition(SQLModel, table=True):
    __tablename__ = "competitions"
    __table_args__ = (
        CheckConstraint("submission_cap_per_day > 0", name="ck_competitions_submission_cap_positive"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(index=True, unique=True, max_length=120)
    title: str = Field(max_length=255)
    description: str = Field(default="", max_length=4000)
    competition_tier: CompetitionTier = Field(
        sa_column=Column(SAEnum(CompetitionTier, name="competition_tier"), nullable=False)
    )
    status: CompetitionStatus = Field(
        default=CompetitionStatus.ACTIVE,
        sa_column=Column(SAEnum(CompetitionStatus, name="competition_status"), nullable=False),
    )
    is_permanent: bool = Field(default=True)
    metric: str = Field(max_length=64)
    higher_is_better: bool = Field(default=True)
    submission_cap_per_day: int = Field(default=10)
    dataset_id: uuid.UUID = Field(foreign_key="datasets.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Submission(SQLModel, table=True):
    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submissions_competition_created", "competition_id", "created_at"),
        Index("ix_submissions_competition_status", "competition_id", "score_status"),
        Index("ix_submissions_competition_user_created", "competition_id", "user_id", "created_at"),
        CheckConstraint("row_count >= 0", name="ck_submissions_row_count_nonnegative"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    competition_id: uuid.UUID = Field(foreign_key="competitions.id", index=True)
    user_id: uuid.UUID = Field(index=True)

    filename: str = Field(max_length=255)
    artifact_path: str = Field(max_length=512)
    artifact_sha256: str = Field(max_length=128)
    row_count: int = Field(default=0)

    score_status: ScoreStatus = Field(
        default=ScoreStatus.QUEUED,
        sa_column=Column(SAEnum(ScoreStatus, name="score_status"), nullable=False),
    )
    leaderboard_score: float | None = Field(default=None)
    score_error: str | None = Field(default=None, max_length=2000)
    scorer_version: str | None = Field(default=None, max_length=64)
    evaluation_split_version: str | None = Field(default=None, max_length=64)

    created_at: datetime = Field(default_factory=utcnow)
    scored_at: datetime | None = Field(default=None)
