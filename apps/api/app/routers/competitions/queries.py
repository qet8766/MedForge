from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import desc
from sqlmodel import Session, select

from app.models import Competition, CompetitionStatus, Dataset, Submission, SubmissionScore

from .errors import competition_not_found, dataset_not_found


def list_active_competitions(session: Session, *, limit: int, offset: int) -> list[Competition]:
    return list(
        session.exec(
            select(Competition)
            .where(Competition.status == CompetitionStatus.ACTIVE)
            .order_by(Competition.slug)
            .offset(offset)
            .limit(limit)
        ).all()
    )


def competition_or_404(session: Session, slug: str, *, for_update: bool = False) -> Competition:
    statement = select(Competition).where(Competition.slug == slug)
    if for_update:
        statement = statement.with_for_update()

    competition = session.exec(statement).first()
    if competition is None:
        raise competition_not_found(slug)
    return competition


def dataset_or_404(session: Session, dataset_id: UUID, *, for_competition_slug: str) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise dataset_not_found(for_competition_slug)
    return dataset


def list_datasets_ordered(session: Session, *, limit: int, offset: int) -> list[Dataset]:
    return list(
        session.exec(
            select(Dataset)
            .order_by(Dataset.slug)
            .offset(offset)
            .limit(limit)
        ).all()
    )


def dataset_by_slug_or_404(session: Session, slug: str) -> Dataset:
    dataset = session.exec(select(Dataset).where(Dataset.slug == slug)).first()
    if dataset is None:
        raise dataset_not_found(slug)
    return dataset


def load_official_scores_for_submissions(
    session: Session,
    submission_ids: Sequence[UUID],
) -> dict[UUID, SubmissionScore]:
    if not submission_ids:
        return {}

    rows = session.exec(
        select(SubmissionScore)
        .where(cast(Any, SubmissionScore.submission_id).in_(submission_ids))
        .where(cast(Any, SubmissionScore.is_official).is_(True))
        .order_by(desc(cast(Any, SubmissionScore.created_at)))
    ).all()

    by_submission: dict[UUID, SubmissionScore] = {}
    for row in rows:
        if row.submission_id not in by_submission:
            by_submission[row.submission_id] = row
    return by_submission


def list_submissions_for_user(
    session: Session,
    *,
    competition_id: UUID,
    user_id: UUID,
    limit: int,
    offset: int,
) -> list[Submission]:
    return list(
        session.exec(
            select(Submission)
            .where(Submission.competition_id == competition_id)
            .where(Submission.user_id == user_id)
            .order_by(desc(cast(Any, Submission.created_at)))
            .offset(offset)
            .limit(limit)
        ).all()
    )
