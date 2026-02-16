from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import CompetitionStatus, CompetitionTier, Role, ScoreStatus, SessionStatus, Tier


class CompetitionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    competition_tier: CompetitionTier
    metric: str
    metric_version: str
    scoring_mode: str
    leaderboard_rule: str
    evaluation_policy: str
    competition_spec_version: str
    is_permanent: bool
    submission_cap_per_day: int


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


class SubmissionScoreRead(BaseModel):
    id: UUID
    primary_score: float
    score_components: dict[str, float]
    scorer_version: str
    metric_version: str
    evaluation_split_version: str
    manifest_sha256: str
    created_at: datetime


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
    tier: Literal["PUBLIC", "PRIVATE"] = "PUBLIC"
    pack_id: UUID | None = None


class SessionActionResponse(BaseModel):
    detail: str


class SessionRead(BaseModel):
    id: UUID
    user_id: UUID
    tier: Tier
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


class SessionCreateResponse(BaseModel):
    detail: str
    session: SessionRead


class SessionCurrentResponse(BaseModel):
    session: SessionRead | None


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class AuthUserResponse(BaseModel):
    user_id: UUID
    email: str
    role: Role
