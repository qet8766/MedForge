from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api_contract import ApiEnvelope, envelope
from app.database import get_session
from app.models import Exposure
from app.pagination import decode_offset_cursor, encode_offset_cursor, validate_limit
from app.schemas import (
    CompetitionDetail,
    CompetitionSummary,
    DatasetDetail,
    DatasetFileEntry,
    DatasetSummary,
    LeaderboardEntry,
    LeaderboardResponse,
    markdown_to_preview,
)

from .dependencies import get_bound_exposure
from .errors import dataset_path_outside_root
from .leaderboard import fetch_leaderboard_rows
from .queries import (
    competition_or_404,
    dataset_by_slug_or_404,
    dataset_or_404,
    list_active_competitions,
    list_datasets_ordered,
)

router = APIRouter()


def _with_preview(summary: CompetitionSummary, description: str) -> CompetitionSummary:
    summary.description_preview = markdown_to_preview(description)
    return summary


@router.get("/competitions", response_model=ApiEnvelope[list[CompetitionSummary]])
def list_competitions(
    request: Request,
    session: Session = Depends(get_session),
    exposure: Exposure = Depends(get_bound_exposure),
    limit: int = 50,
    cursor: str | None = None,
) -> ApiEnvelope[list[CompetitionSummary]]:
    limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)
    competitions = list_active_competitions(session, exposure=exposure, limit=limit + 1, offset=offset)
    has_more = len(competitions) > limit
    page = competitions[:limit]
    next_cursor = encode_offset_cursor(offset + limit) if has_more else None
    return envelope(
        request,
        [
            _with_preview(CompetitionSummary.model_validate(competition), competition.description)
            for competition in page
        ],
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/competitions/{slug}", response_model=ApiEnvelope[CompetitionDetail])
def get_competition(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
    exposure: Exposure = Depends(get_bound_exposure),
) -> ApiEnvelope[CompetitionDetail]:
    competition = competition_or_404(session, slug, exposure=exposure)
    dataset = dataset_or_404(session, competition.dataset_id, for_competition_slug=competition.slug)
    return envelope(
        request,
        CompetitionDetail(
            **CompetitionSummary.model_validate(competition).model_dump(),
            description=competition.description,
            status=competition.status,
            dataset_slug=dataset.slug,
            dataset_title=dataset.title,
        ),
    )


@router.get("/competitions/{slug}/leaderboard", response_model=ApiEnvelope[LeaderboardResponse])
def get_leaderboard(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
    exposure: Exposure = Depends(get_bound_exposure),
    limit: int = 50,
    cursor: str | None = None,
) -> ApiEnvelope[LeaderboardResponse]:
    limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)

    competition = competition_or_404(session, slug, exposure=exposure)
    rows = fetch_leaderboard_rows(
        session,
        competition=competition,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = encode_offset_cursor(offset + limit) if has_more else None

    entries = [
        LeaderboardEntry(
            rank=rank_index,
            user_id=row.user_id,
            best_submission_id=row.submission_id,
            best_score_id=row.score_id,
            primary_score=row.primary_score,
            metric_version=row.metric_version,
            evaluation_split_version=row.evaluation_split_version,
            scored_at=row.scored_at,
        )
        for rank_index, row in enumerate(page, start=offset + 1)
    ]
    return envelope(
        request,
        LeaderboardResponse(competition_slug=competition.slug, entries=entries),
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/datasets", response_model=ApiEnvelope[list[DatasetSummary]])
def list_datasets(
    request: Request,
    session: Session = Depends(get_session),
    exposure: Exposure = Depends(get_bound_exposure),
    limit: int = 50,
    cursor: str | None = None,
) -> ApiEnvelope[list[DatasetSummary]]:
    limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)
    datasets = list_datasets_ordered(session, exposure=exposure, limit=limit + 1, offset=offset)
    has_more = len(datasets) > limit
    page = datasets[:limit]
    next_cursor = encode_offset_cursor(offset + limit) if has_more else None
    return envelope(
        request,
        [DatasetSummary.model_validate(dataset) for dataset in page],
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/datasets/{slug}", response_model=ApiEnvelope[DatasetDetail])
def get_dataset(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
    exposure: Exposure = Depends(get_bound_exposure),
) -> ApiEnvelope[DatasetDetail]:
    dataset = dataset_by_slug_or_404(session, slug, exposure=exposure)
    return envelope(request, DatasetDetail.model_validate(dataset))


@router.get("/datasets/{slug}/files", response_model=ApiEnvelope[list[DatasetFileEntry]])
def list_dataset_files(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
    exposure: Exposure = Depends(get_bound_exposure),
) -> ApiEnvelope[list[DatasetFileEntry]]:
    dataset = dataset_by_slug_or_404(session, slug, exposure=exposure)
    training_root = Path(dataset.storage_path)
    training_root_resolved = training_root.resolve()

    if not training_root_resolved.is_dir():
        return envelope(request, [])

    entries: list[DatasetFileEntry] = []
    for child in sorted(training_root_resolved.iterdir(), key=lambda p: (p.is_file(), p.name)):
        try:
            child.resolve().relative_to(training_root_resolved)
        except ValueError:
            raise dataset_path_outside_root(slug)
        if child.is_file():
            entries.append(DatasetFileEntry(name=child.name, size=child.stat().st_size, type="file"))
        elif child.is_dir():
            dir_size = sum(f.stat().st_size for f in child.rglob("*") if f.is_file())
            entries.append(DatasetFileEntry(name=child.name, size=dir_size, type="directory"))
    return envelope(request, entries)
