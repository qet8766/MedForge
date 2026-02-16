from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import CompetitionStatus, Role, ScoreStatus, SessionStatus


def _lower_enum_value(value: object) -> str:
    if hasattr(value, "value"):
        value = value.value
    if not isinstance(value, str):
        raise TypeError("Expected enum/string value.")
    return value.lower()


class CompetitionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    competition_tier: Literal["public", "private"]
    metric: str
    metric_version: str
    scoring_mode: str
    leaderboard_rule: str
    evaluation_policy: str
    competition_spec_version: str
    is_permanent: bool
    submission_cap_per_day: int

    @field_validator("competition_tier", mode="before")
    @classmethod
    def normalize_competition_tier(cls, value: object) -> str:
        return _lower_enum_value(value)


class CompetitionDetail(CompetitionSummary):
    description: str
    status: CompetitionStatus
    dataset_slug: str
    dataset_title: str


class DatasetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    source: str


class DatasetDetail(DatasetSummary):
    license: str
    storage_path: str
    bytes: int
    checksum: str


class SubmissionScoreRead(BaseModel):
    id: UUID
    primary_score: float
    score_components: dict[str, float]
    scorer_version: str
    metric_version: str
    evaluation_split_version: str
    manifest_sha256: str
    created_at: datetime


class SubmissionRead(BaseModel):
    id: UUID
    competition_slug: str
    user_id: UUID
    filename: str
    score_status: ScoreStatus
    score_error: str | None
    created_at: datetime
    scored_at: datetime | None
    official_score: SubmissionScoreRead | None


class SubmissionCreateResponse(BaseModel):
    submission: SubmissionRead
    daily_cap: int
    remaining_today: int


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    best_submission_id: UUID
    best_score_id: UUID
    primary_score: float
    metric_version: str
    evaluation_split_version: str
    scored_at: datetime | None


class LeaderboardResponse(BaseModel):
    competition_slug: str
    entries: list[LeaderboardEntry]


class MeResponse(BaseModel):
    user_id: UUID
    role: Role
    email: str | None = None


class SessionCreateRequest(BaseModel):
    tier: Literal["public", "private"] = "public"
    pack_id: UUID | None = None


class SessionActionResponse(BaseModel):
    message: str


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    tier: Literal["public", "private"]
    pack_id: UUID
    status: SessionStatus
    container_id: str | None
    gpu_id: int
    slug: str
    workspace_zfs: str
    created_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None
    error_message: str | None

    @field_validator("tier", mode="before")
    @classmethod
    def normalize_tier(cls, value: object) -> str:
        return _lower_enum_value(value)


class SessionCreateResponse(BaseModel):
    message: str
    session: SessionRead


class SessionCurrentResponse(BaseModel):
    session: SessionRead | None


class AuthCredentials(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class AuthUserResponse(BaseModel):
    user_id: UUID
    email: str
    role: Role


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
