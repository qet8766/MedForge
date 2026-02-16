from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import asc, desc, func
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.database import get_session
from app.deps import get_current_user_id, require_admin_access, require_allowed_origin
from app.models import Competition, CompetitionStatus, Dataset, ScoreStatus, Submission, SubmissionScore
from app.schemas import (
    CompetitionDetail,
    CompetitionSummary,
    DatasetDetail,
    DatasetSummary,
    LeaderboardEntry,
    LeaderboardResponse,
    SubmissionCreateResponse,
    SubmissionRead,
    SubmissionScoreRead,
)
from app.scoring import validate_submission_schema
from app.services import enforce_submission_cap, process_submission_by_id
from app.storage import SubmissionUploadTooLargeError, store_submission_file

router = APIRouter(prefix="/api", tags=["competitions"])


def _competition_or_404(session: Session, slug: str, *, for_update: bool = False) -> Competition:
    statement = select(Competition).where(Competition.slug == slug)
    if for_update:
        statement = statement.with_for_update()

    competition = session.exec(statement).first()
    if competition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found.")
    return competition


def _dataset_or_404(session: Session, dataset_id: UUID) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    return dataset


def _score_components(score: SubmissionScore) -> dict[str, float]:
    payload = json.loads(score.score_components_json)
    if not isinstance(payload, dict):
        raise ValueError("score_components_json must decode to an object.")
    mapped: dict[str, float] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            raise ValueError("score component key must be a string.")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("score component value must be numeric.")
        mapped[key] = float(value)
    return mapped


def _score_to_read(score: SubmissionScore) -> SubmissionScoreRead:
    return SubmissionScoreRead(
        id=score.id,
        primary_score=score.primary_score,
        score_components=_score_components(score),
        scorer_version=score.scorer_version,
        metric_version=score.metric_version,
        evaluation_split_version=score.evaluation_split_version,
        manifest_sha256=score.manifest_sha256,
        created_at=score.created_at,
    )


def _to_submission_read(
    submission: Submission,
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
        official_score=_score_to_read(official_score) if official_score is not None else None,
    )


def _mark_submission_failed(session: Session, submission: Submission, error: str) -> None:
    submission.score_status = ScoreStatus.FAILED
    submission.score_error = error
    session.add(submission)
    session.commit()
    session.refresh(submission)


def _load_official_scores_for_submissions(
    session: Session,
    submission_ids: Sequence[UUID],
) -> dict[UUID, SubmissionScore]:
    if not submission_ids:
        return {}

    rows = session.exec(
        select(SubmissionScore)
        .where(SubmissionScore.submission_id.in_(submission_ids))
        .where(SubmissionScore.is_official.is_(True))
        .order_by(desc(cast(Any, SubmissionScore.created_at)))
    ).all()

    by_submission: dict[UUID, SubmissionScore] = {}
    for row in rows:
        if row.submission_id not in by_submission:
            by_submission[row.submission_id] = row
    return by_submission


@router.get("/competitions", response_model=list[CompetitionSummary])
def list_competitions(session: Session = Depends(get_session)) -> list[CompetitionSummary]:
    competitions = session.exec(
        select(Competition).where(Competition.status == CompetitionStatus.ACTIVE).order_by(Competition.slug)
    ).all()

    return [
        CompetitionSummary(
            slug=competition.slug,
            title=competition.title,
            competition_tier=competition.competition_tier,
            metric=competition.metric,
            metric_version=competition.metric_version,
            scoring_mode=competition.scoring_mode,
            leaderboard_rule=competition.leaderboard_rule,
            evaluation_policy=competition.evaluation_policy,
            competition_spec_version=competition.competition_spec_version,
            is_permanent=competition.is_permanent,
            submission_cap_per_day=competition.submission_cap_per_day,
        )
        for competition in competitions
    ]


@router.get("/competitions/{slug}", response_model=CompetitionDetail)
def get_competition(slug: str, session: Session = Depends(get_session)) -> CompetitionDetail:
    competition = _competition_or_404(session, slug)
    dataset = _dataset_or_404(session, competition.dataset_id)
    return CompetitionDetail(
        slug=competition.slug,
        title=competition.title,
        competition_tier=competition.competition_tier,
        metric=competition.metric,
        metric_version=competition.metric_version,
        scoring_mode=competition.scoring_mode,
        leaderboard_rule=competition.leaderboard_rule,
        evaluation_policy=competition.evaluation_policy,
        competition_spec_version=competition.competition_spec_version,
        is_permanent=competition.is_permanent,
        submission_cap_per_day=competition.submission_cap_per_day,
        description=competition.description,
        status=competition.status,
        dataset_slug=dataset.slug,
        dataset_title=dataset.title,
    )


@router.get("/competitions/{slug}/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(
    slug: str,
    session: Session = Depends(get_session),
    limit: int = 50,
    offset: int = 0,
) -> LeaderboardResponse:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be 1..500")
    if offset < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="offset must be >= 0")

    competition = _competition_or_404(session, slug)

    score_col = cast(Any, SubmissionScore.primary_score)
    created_col = cast(Any, SubmissionScore.created_at)
    submission_id_col = cast(Any, Submission.id)
    score_order = desc(score_col) if competition.higher_is_better else asc(score_col)

    ranked_per_user = (
        select(
            Submission.user_id.label("user_id"),
            Submission.id.label("submission_id"),
            SubmissionScore.id.label("score_id"),
            SubmissionScore.primary_score.label("primary_score"),
            SubmissionScore.metric_version.label("metric_version"),
            SubmissionScore.evaluation_split_version.label("evaluation_split_version"),
            SubmissionScore.created_at.label("scored_at"),
            func.row_number()
            .over(
                partition_by=Submission.user_id,
                order_by=(score_order, asc(created_col), asc(submission_id_col)),
            )
            .label("user_rank"),
        )
        .join(Submission, Submission.id == SubmissionScore.submission_id)
        .where(Submission.competition_id == competition.id)
        .where(Submission.score_status == ScoreStatus.SCORED)
        .where(SubmissionScore.is_official.is_(True))
    ).subquery()

    leaderboard_order_score = (
        desc(cast(Any, ranked_per_user.c.primary_score))
        if competition.higher_is_better
        else asc(cast(Any, ranked_per_user.c.primary_score))
    )
    rows = session.exec(
        select(
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

    entries: list[LeaderboardEntry] = []
    for rank_index, row in enumerate(rows, start=offset + 1):
        entries.append(
            LeaderboardEntry(
                rank=rank_index,
                user_id=row.user_id,
                best_submission_id=row.submission_id,
                best_score_id=row.score_id,
                primary_score=float(row.primary_score),
                metric_version=row.metric_version,
                evaluation_split_version=row.evaluation_split_version,
                scored_at=row.scored_at,
            )
        )

    return LeaderboardResponse(competition_slug=competition.slug, entries=entries)


@router.post("/competitions/{slug}/submissions", response_model=SubmissionCreateResponse)
async def create_submission(
    slug: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _origin_guard: None = Depends(require_allowed_origin),
    user_id: UUID = Depends(get_current_user_id),
) -> SubmissionCreateResponse:
    competition = _competition_or_404(session, slug, for_update=True)
    remaining_before = enforce_submission_cap(session, competition=competition, user_id=user_id)

    submission = Submission(
        competition_id=competition.id,
        user_id=user_id,
        filename=file.filename or "submission.csv",
        artifact_path="",
        artifact_sha256="",
        row_count=0,
        score_status=ScoreStatus.QUEUED,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    try:
        stored = await store_submission_file(
            settings=settings,
            competition_slug=competition.slug,
            user_id=user_id,
            submission_id=submission.id,
            upload=file,
        )
        validate_submission_schema(competition.slug, stored.path)

        submission.artifact_path = str(stored.path)
        submission.artifact_sha256 = stored.sha256
        submission.row_count = stored.row_count
        session.add(submission)
        session.commit()
        session.refresh(submission)
    except SubmissionUploadTooLargeError as exc:
        _mark_submission_failed(session, submission, str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {
                    "loc": ["body", "file"],
                    "msg": str(exc),
                    "type": "value_error.submission_too_large",
                    "ctx": {
                        "max_bytes": exc.max_bytes,
                        "size_bytes": exc.size_bytes,
                    },
                }
            ],
        ) from exc
    except Exception as exc:
        _mark_submission_failed(session, submission, str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    if settings.auto_score_on_submit:
        submission = process_submission_by_id(session, submission_id=submission.id, settings=settings) or submission

    remaining_after = max(0, remaining_before - 1)
    official_score = _load_official_scores_for_submissions(session, [submission.id]).get(submission.id)

    return SubmissionCreateResponse(
        submission=_to_submission_read(submission, competition.slug, official_score),
        daily_cap=competition.submission_cap_per_day,
        remaining_today=remaining_after,
    )


@router.get("/competitions/{slug}/submissions/me", response_model=list[SubmissionRead])
def list_my_submissions(
    slug: str,
    session: Session = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[SubmissionRead]:
    competition = _competition_or_404(session, slug)
    submissions = session.exec(
        select(Submission)
        .where(Submission.competition_id == competition.id)
        .where(Submission.user_id == user_id)
        .order_by(desc(cast(Any, Submission.created_at)))
    ).all()
    scores = _load_official_scores_for_submissions(session, [submission.id for submission in submissions])

    return [
        _to_submission_read(submission, competition.slug, scores.get(submission.id))
        for submission in submissions
    ]


@router.get("/datasets", response_model=list[DatasetSummary])
def list_datasets(session: Session = Depends(get_session)) -> list[DatasetSummary]:
    datasets = session.exec(select(Dataset).order_by(Dataset.slug)).all()
    return [DatasetSummary(slug=dataset.slug, title=dataset.title, source=dataset.source) for dataset in datasets]


@router.get("/datasets/{slug}", response_model=DatasetDetail)
def get_dataset(slug: str, session: Session = Depends(get_session)) -> DatasetDetail:
    dataset = session.exec(select(Dataset).where(Dataset.slug == slug)).first()
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    return DatasetDetail(
        slug=dataset.slug,
        title=dataset.title,
        source=dataset.source,
        license=dataset.license,
        storage_path=dataset.storage_path,
        bytes=dataset.bytes,
        checksum=dataset.checksum,
    )


@router.post("/admin/submissions/{submission_id}/score", response_model=SubmissionRead)
def score_submission_once(
    submission_id: UUID,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _origin_guard: None = Depends(require_allowed_origin),
    _admin: None = Depends(require_admin_access),
) -> SubmissionRead:
    submission = process_submission_by_id(session, submission_id=submission_id, settings=settings)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    competition = session.get(Competition, submission.competition_id)
    if competition is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Competition missing.")

    official_score = _load_official_scores_for_submissions(session, [submission.id]).get(submission.id)
    return _to_submission_read(submission, competition.slug, official_score)
