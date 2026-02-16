from __future__ import annotations

import json

from app.models import Submission, SubmissionScore
from app.schemas import SubmissionRead, SubmissionScoreRead

from .errors import corrupted_score_components


def score_components(score: SubmissionScore) -> dict[str, float]:
    try:
        payload = json.loads(score.score_components_json)
    except json.JSONDecodeError as exc:
        raise corrupted_score_components(score.id) from exc

    if not isinstance(payload, dict):
        raise corrupted_score_components(score.id)

    try:
        return {str(key): float(value) for key, value in payload.items()}
    except (TypeError, ValueError) as exc:
        raise corrupted_score_components(score.id) from exc


def score_to_read(score: SubmissionScore) -> SubmissionScoreRead:
    return SubmissionScoreRead(
        id=score.id,
        primary_score=score.primary_score,
        score_components=score_components(score),
        scorer_version=score.scorer_version,
        metric_version=score.metric_version,
        evaluation_split_version=score.evaluation_split_version,
        manifest_sha256=score.manifest_sha256,
        created_at=score.created_at,
    )


def submission_to_read(
    submission: Submission,
    *,
    competition_slug: str,
    official_score: SubmissionScore | None,
) -> SubmissionRead:
    return SubmissionRead(
        id=submission.id,
        competition_slug=competition_slug,
        user_id=submission.user_id,
        filename=submission.filename,
        score_status=submission.score_status,
        score_error=submission.score_error,
        created_at=submission.created_at,
        scored_at=submission.scored_at,
        official_score=score_to_read(official_score) if official_score is not None else None,
    )
