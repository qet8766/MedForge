from __future__ import annotations

from datetime import datetime
from typing import Any, NamedTuple, cast
from uuid import UUID

from sqlalchemy import asc, desc, func
from sqlmodel import Session, select

from app.models import Competition, ScoreStatus, Submission, SubmissionScore


class LeaderboardRow(NamedTuple):
    user_id: UUID
    submission_id: UUID
    score_id: UUID
    primary_score: float
    metric_version: str
    evaluation_split_version: str
    scored_at: datetime | None


def fetch_leaderboard_rows(
    session: Session,
    *,
    competition: Competition,
    limit: int,
    offset: int,
) -> list[LeaderboardRow]:
    select_any = cast(Any, select)
    submission_user_col = cast(Any, Submission.user_id)
    submission_id_col = cast(Any, Submission.id)
    submission_competition_id_col = cast(Any, Submission.competition_id)
    submission_score_status_col = cast(Any, Submission.score_status)
    submission_score_submission_id_col = cast(Any, SubmissionScore.submission_id)
    score_id_col = cast(Any, SubmissionScore.id)
    score_col = cast(Any, SubmissionScore.primary_score)
    metric_version_col = cast(Any, SubmissionScore.metric_version)
    evaluation_split_version_col = cast(Any, SubmissionScore.evaluation_split_version)
    created_col = cast(Any, SubmissionScore.created_at)
    is_official_col = cast(Any, SubmissionScore.is_official)
    score_order = desc(score_col) if competition.higher_is_better else asc(score_col)

    ranked_per_user = (
        select_any(
            submission_user_col.label("user_id"),
            submission_id_col.label("submission_id"),
            score_id_col.label("score_id"),
            score_col.label("primary_score"),
            metric_version_col.label("metric_version"),
            evaluation_split_version_col.label("evaluation_split_version"),
            created_col.label("scored_at"),
            func.row_number()
            .over(
                partition_by=submission_user_col,
                order_by=(score_order, asc(created_col), asc(submission_id_col)),
            )
            .label("user_rank"),
        )
        .join(Submission, submission_id_col == submission_score_submission_id_col)
        .where(submission_competition_id_col == competition.id)
        .where(submission_score_status_col == ScoreStatus.SCORED)
        .where(is_official_col.is_(True))
    ).subquery()

    leaderboard_order_score = (
        desc(cast(Any, ranked_per_user.c.primary_score))
        if competition.higher_is_better
        else asc(cast(Any, ranked_per_user.c.primary_score))
    )

    rows = session.exec(
        select_any(
            ranked_per_user.c.user_id,
            ranked_per_user.c.submission_id,
            ranked_per_user.c.score_id,
            ranked_per_user.c.primary_score,
            ranked_per_user.c.metric_version,
            ranked_per_user.c.evaluation_split_version,
            ranked_per_user.c.scored_at,
        )
        .where(ranked_per_user.c.user_rank == 1)
        .order_by(
            leaderboard_order_score,
            asc(cast(Any, ranked_per_user.c.scored_at)),
            asc(cast(Any, ranked_per_user.c.submission_id)),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    return [
        LeaderboardRow(
            user_id=row.user_id,
            submission_id=row.submission_id,
            score_id=row.score_id,
            primary_score=float(row.primary_score),
            metric_version=row.metric_version,
            evaluation_split_version=row.evaluation_split_version,
            scored_at=row.scored_at,
        )
        for row in rows
    ]
