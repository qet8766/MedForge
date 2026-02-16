from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api_contract import ApiEnvelope, envelope
from app.database import get_session
from app.pagination import decode_offset_cursor, encode_offset_cursor, validate_limit
from app.schemas import (
    CompetitionDetail,
    CompetitionSummary,
    DatasetDetail,
    DatasetSummary,
    LeaderboardEntry,
    LeaderboardResponse,
)

from .leaderboard import fetch_leaderboard_rows
from .queries import (
    competition_or_404,
    dataset_by_slug_or_404,
    dataset_or_404,
    list_active_competitions,
    list_datasets_ordered,
)

router = APIRouter()


@router.get("/competitions", response_model=ApiEnvelope[list[CompetitionSummary]])
def list_competitions(
    request: Request,
    session: Session = Depends(get_session),
    limit: int = 50,
    cursor: str | None = None,
) -> ApiEnvelope[list[CompetitionSummary]]:
    limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)
    competitions = list_active_competitions(session, limit=limit + 1, offset=offset)
    has_more = len(competitions) > limit
    page = competitions[:limit]
    next_cursor = encode_offset_cursor(offset + limit) if has_more else None
    return envelope(
        request,
        [CompetitionSummary.model_validate(competition) for competition in page],
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/competitions/{slug}", response_model=ApiEnvelope[CompetitionDetail])
def get_competition(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
) -> ApiEnvelope[CompetitionDetail]:
    competition = competition_or_404(session, slug)
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
    limit: int = 50,
    cursor: str | None = None,
) -> ApiEnvelope[LeaderboardResponse]:
    limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)

    competition = competition_or_404(session, slug)
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
    limit: int = 50,
    cursor: str | None = None,
) -> ApiEnvelope[list[DatasetSummary]]:
    limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)
    datasets = list_datasets_ordered(session, limit=limit + 1, offset=offset)
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
) -> ApiEnvelope[DatasetDetail]:
    dataset = dataset_by_slug_or_404(session, slug)
    return envelope(request, DatasetDetail.model_validate(dataset))
