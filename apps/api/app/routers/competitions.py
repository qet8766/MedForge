from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import asc, desc
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.database import get_session
from app.deps import get_current_user_id, require_admin_access, require_allowed_origin
from app.models import Competition, CompetitionStatus, Dataset, ScoreStatus, Submission
from app.schemas import (
    CompetitionDetail,
    CompetitionSummary,
    DatasetDetail,
    DatasetSummary,
    LeaderboardEntry,
    LeaderboardResponse,
    SubmissionCreateResponse,
    SubmissionRead,
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


def _to_submission_read(submission: Submission, competition_slug: str) -> SubmissionRead:
    return SubmissionRead(
        id=submission.id,
        competition_slug=competition_slug,
        user_id=submission.user_id,
        filename=submission.filename,
        score_status=submission.score_status,
        leaderboard_score=submission.leaderboard_score,
        score_error=submission.score_error,
        created_at=submission.created_at,
        scored_at=submission.scored_at,
    )


def _mark_submission_failed(session: Session, submission: Submission, error: str) -> None:
    submission.score_status = ScoreStatus.FAILED
    submission.score_error = error
    session.add(submission)
    session.commit()
    session.refresh(submission)


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
            scoring_mode=competition.scoring_mode,
            leaderboard_rule=competition.leaderboard_rule,
            evaluation_policy=competition.evaluation_policy,
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
        scoring_mode=competition.scoring_mode,
        leaderboard_rule=competition.leaderboard_rule,
        evaluation_policy=competition.evaluation_policy,
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

    score_col = cast(Any, Submission.leaderboard_score)
    created_col = cast(Any, Submission.created_at)
    score_order = desc(score_col) if competition.higher_is_better else asc(score_col)

    submissions = session.exec(
        select(Submission)
        .where(Submission.competition_id == competition.id)
        .where(Submission.score_status == ScoreStatus.SCORED)
        .where(score_col.is_not(None))
        .order_by(score_order, asc(created_col))
    ).all()

    best_by_user: dict[UUID, Submission] = {}
    for submission in submissions:
        if submission.user_id in best_by_user:
            continue
        best_by_user[submission.user_id] = submission

    entries: list[LeaderboardEntry] = []
    ranked = list(best_by_user.values())
    paged = ranked[offset : offset + limit]

    for rank_index, submission in enumerate(paged, start=offset + 1):
        entries.append(
            LeaderboardEntry(
                rank=rank_index,
                user_id=submission.user_id,
                best_submission_id=submission.id,
                leaderboard_score=float(submission.leaderboard_score or 0.0),
                scored_at=submission.scored_at,
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

    return SubmissionCreateResponse(
        submission=_to_submission_read(submission, competition.slug),
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

    return [_to_submission_read(submission, competition.slug) for submission in submissions]


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

    return _to_submission_read(submission, competition.slug)
