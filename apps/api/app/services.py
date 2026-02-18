from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.config import Settings
from app.models import Competition, ScoreStatus, Submission, SubmissionScore
from app.scoring import SCORER_VERSION, score_submission_file

log = logging.getLogger("medforge.services")


def utc_day_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or datetime.now(UTC)
    start = datetime(current.year, current.month, current.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start, end


def count_user_submissions_today(session: Session, *, competition_id: UUID, user_id: UUID) -> int:
    start, end = utc_day_bounds()
    statement = (
        select(func.count())
        .select_from(Submission)
        .where(Submission.competition_id == competition_id)
        .where(Submission.user_id == user_id)
        .where(Submission.created_at >= start)
        .where(Submission.created_at < end)
    )
    return int(session.exec(statement).one())


def enforce_submission_cap(session: Session, *, competition: Competition, user_id: UUID) -> int:
    count_today = count_user_submissions_today(
        session,
        competition_id=competition.id,
        user_id=user_id,
    )
    remaining = competition.submission_cap_per_day - count_today
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Daily submission cap reached for {competition.slug}. "
                f"Limit: {competition.submission_cap_per_day}/day."
            ),
        )
    return remaining


def get_competition_paths(settings: Settings, slug: str) -> tuple[Path, Path]:
    labels_path = settings.test_holdouts_dir / slug / "holdout_labels.csv"
    manifest_path = settings.public_eval_data_root / slug / "manifest.json"
    return labels_path, manifest_path


def process_submission_by_id(session: Session, *, submission_id: UUID, settings: Settings) -> Submission | None:
    submission = session.get(Submission, submission_id)
    if submission is None:
        return None

    if submission.score_status not in (ScoreStatus.QUEUED, ScoreStatus.FAILED, ScoreStatus.SCORING):
        return submission

    competition = session.get(Competition, submission.competition_id)
    if competition is None:
        submission.score_status = ScoreStatus.FAILED
        submission.score_error = "Competition not found for submission."
        session.add(submission)
        session.commit()
        session.refresh(submission)
        return submission

    submission.score_status = ScoreStatus.SCORING
    submission.score_error = None
    session.add(submission)
    session.commit()
    session.refresh(submission)

    labels_path, manifest_path = get_competition_paths(settings, competition.slug)

    try:
        result = score_submission_file(
            competition=competition,
            submission_path=Path(submission.artifact_path),
            labels_path=labels_path,
            manifest_path=manifest_path,
        )
        is_official_col = cast(Any, SubmissionScore.is_official)
        previous_official_scores = session.exec(
            select(SubmissionScore)
            .where(SubmissionScore.submission_id == submission.id)
            .where(is_official_col.is_(True))
        ).all()
        for previous in previous_official_scores:
            previous.is_official = False
            session.add(previous)

        score_run = SubmissionScore(
            submission_id=submission.id,
            competition_id=competition.id,
            user_id=submission.user_id,
            is_official=True,
            primary_score=result.primary_score,
            score_components_json=json.dumps(result.score_components, sort_keys=True, separators=(",", ":")),
            scorer_version=SCORER_VERSION,
            metric_version=result.metric_version,
            evaluation_split_version=result.evaluation_split_version,
            manifest_sha256=result.manifest_sha256,
            created_at=datetime.now(UTC),
        )
        session.add(score_run)

        submission.score_status = ScoreStatus.SCORED
        submission.scored_at = datetime.now(UTC)
        submission.score_error = None
    except Exception as exc:
        log.exception(
            "scoring failed submission=%s user=%s competition=%s",
            submission.id,
            submission.user_id,
            competition.slug,
        )
        submission.score_status = ScoreStatus.FAILED
        submission.score_error = str(exc)
        submission.scored_at = datetime.now(UTC)

    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission
