from __future__ import annotations

import hashlib
from pathlib import Path

from app.models import Competition

from .competition_specs import get_competition_spec
from .csv_io import _read_csv_rows
from .manifest import (
    _load_manifest,
    _validate_label_row_count,
    _validate_manifest_contract,
)
from .types import ScoreResult


def validate_submission_schema(competition_slug: str, submission_path: Path) -> None:
    rows = _read_csv_rows(submission_path)
    spec = get_competition_spec(competition_slug)
    spec.validate_submission_rows(rows)


def score_submission_file(
    *,
    competition: Competition,
    submission_path: Path,
    labels_path: Path,
    manifest_path: Path,
) -> ScoreResult:
    submission_rows = _read_csv_rows(submission_path)
    label_rows = _read_csv_rows(labels_path)

    manifest = _load_manifest(manifest_path)
    _validate_label_row_count(label_rows, manifest)

    spec = get_competition_spec(competition.slug)
    if competition.metric != spec.metric:
        raise ValueError(
            f"Competition metric mismatch: competition={competition.metric}, scorer={spec.metric}"
        )
    spec.validate_submission_rows(submission_rows)
    spec.validate_label_columns(label_rows)
    _validate_manifest_contract(
        manifest,
        expected_id_column=spec.manifest_id_column,
        expected_target_columns=spec.manifest_target_columns,
    )

    labels = spec.parse_labels(label_rows)
    predictions = spec.parse_submission(submission_rows)
    score = spec.score_fn(labels, predictions)
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    return ScoreResult(
        primary_score=score,
        score_components={"primary": score},
        metric_version=spec.metric_version,
        evaluation_split_version=manifest.evaluation_split_version,
        manifest_sha256=manifest_sha256,
    )
