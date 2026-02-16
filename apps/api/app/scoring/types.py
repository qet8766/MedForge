from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    primary_score: float
    score_components: dict[str, float]
    metric_version: str
    evaluation_split_version: str
    manifest_sha256: str


@dataclass(frozen=True)
class ManifestMetadata:
    evaluation_split_version: str
    scoring_mode: str
    leaderboard_rule: str
    evaluation_policy: str
    id_column: str
    target_columns: tuple[str, ...]
    expected_row_count: int


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float
    confidence: float = 0.0
