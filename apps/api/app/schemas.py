from __future__ import annotations

import re
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


def markdown_to_preview(description: str, max_len: int = 200) -> str:
    """Strip markdown syntax and truncate for card previews."""
    text = re.sub(r"#{1,6}\s+", "", description)  # headings
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)  # bold/italic
    text = re.sub(r"`([^`]+)`", r"\1", text)  # inline code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    text = re.sub(r"[-*+]\s+", "", text)  # list markers
    text = re.sub(r"\d+\.\s+", "", text)  # numbered lists
    text = re.sub(r"\n+", " ", text)  # newlines to spaces
    text = re.sub(r"\s+", " ", text).strip()  # collapse whitespace
    if len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(" ", 1)[0]
    return truncated + "..." if truncated else text[:max_len] + "..."


class CompetitionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    competition_exposure: Literal["external", "internal"]
    metric: str
    metric_version: str
    scoring_mode: str
    leaderboard_rule: str
    evaluation_policy: str
    competition_spec_version: str
    is_permanent: bool
    submission_cap_per_day: int
    description_preview: str = ""

    @field_validator("competition_exposure", mode="before")
    @classmethod
    def normalize_competition_exposure(cls, value: object) -> str:
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
    exposure: Literal["external", "internal"]

    @field_validator("exposure", mode="before")
    @classmethod
    def normalize_dataset_exposure(cls, value: object) -> str:
        return _lower_enum_value(value)


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
    can_use_internal: bool
    ssh_public_key: str | None = None


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: UUID | None = None


class SessionActionResponse(BaseModel):
    message: str


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    exposure: Literal["external", "internal"]
    pack_id: UUID
    status: SessionStatus
    container_id: str | None
    gpu_id: int
    ssh_port: int
    ssh_host: str = ""
    slug: str
    workspace_zfs: str
    created_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None
    error_message: str | None

    @field_validator("exposure", mode="before")
    @classmethod
    def normalize_exposure(cls, value: object) -> str:
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
    can_use_internal: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]


class UserAdminRead(BaseModel):
    user_id: UUID
    email: str
    role: Role
    can_use_internal: bool
    max_concurrent_sessions: int
    created_at: datetime
    active_session_count: int


class UserAdminUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role | None = None
    can_use_internal: bool | None = None
    max_concurrent_sessions: int | None = Field(default=None, ge=1, le=8)


class MeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = Field(default=None, max_length=320)
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    ssh_public_key: str | None = Field(default=None, max_length=4096)


class DatasetFileEntry(BaseModel):
    name: str
    size: int
    type: Literal["file", "directory"]
