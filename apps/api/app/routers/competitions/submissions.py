from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlmodel import Session

from app.api_contract import ApiEnvelope, envelope
from app.config import Settings, get_settings
from app.database import get_session
from app.models import Exposure
from app.pagination import decode_offset_cursor, encode_offset_cursor, validate_limit
from app.schemas import SubmissionCreateResponse, SubmissionRead
from app.scoring import validate_submission_schema
from app.services import enforce_submission_cap, process_submission_by_id
from app.storage import SubmissionUploadTooLargeError, store_submission_file

from .dependencies import get_bound_exposure, get_current_user_id_checked, require_allowed_origin_checked
from .errors import (
    from_http_exception,
    submission_processing_failed,
    submission_too_large,
    submission_validation_failed,
)
from .mappers import submission_to_read
from .queries import (
    competition_or_404,
    list_submissions_for_user,
    load_official_scores_for_submissions,
)
from .submission_records import create_queued_submission, mark_submission_failed, persist_stored_submission

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/competitions/{slug}/submissions",
    response_model=ApiEnvelope[SubmissionCreateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    request: Request,
    slug: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    exposure: Exposure = Depends(get_bound_exposure),
    _origin_guard: None = Depends(require_allowed_origin_checked),
    user_id: UUID = Depends(get_current_user_id_checked),
) -> ApiEnvelope[SubmissionCreateResponse]:
    competition = competition_or_404(session, slug, exposure=exposure, for_update=True)

    try:
        remaining_before = enforce_submission_cap(session, competition=competition, user_id=user_id)
    except HTTPException as exc:
        raise from_http_exception(exc, type_slug="submission-cap-reached") from exc

    submission = create_queued_submission(
        session,
        competition_id=competition.id,
        user_id=user_id,
        filename=file.filename or "submission.csv",
    )

    try:
        stored = await store_submission_file(
            settings=settings,
            competition_slug=competition.slug,
            user_id=user_id,
            submission_id=submission.id,
            upload=file,
        )
        validate_submission_schema(competition.slug, stored.path)
        submission = persist_stored_submission(session, submission=submission, stored=stored)
    except SubmissionUploadTooLargeError as exc:
        mark_submission_failed(session, submission=submission, error=str(exc))
        raise submission_too_large(exc) from exc
    except ValueError as exc:
        mark_submission_failed(session, submission=submission, error=str(exc))
        raise submission_validation_failed(str(exc)) from exc
    except Exception as exc:
        mark_submission_failed(session, submission=submission, error=str(exc))
        logger.exception(
            "competition.submission.create_failed",
            competition_slug=competition.slug,
            user_id=str(user_id),
            submission_id=str(submission.id),
            error=str(exc),
        )
        raise submission_processing_failed() from exc

    if settings.auto_score_on_submit:
        submission = process_submission_by_id(session, submission_id=submission.id, settings=settings) or submission

    remaining_after = max(0, remaining_before - 1)
    official_score = load_official_scores_for_submissions(session, [submission.id]).get(submission.id)
    return envelope(
        request,
        SubmissionCreateResponse(
            submission=submission_to_read(
                submission,
                competition_slug=competition.slug,
                official_score=official_score,
            ),
            daily_cap=competition.submission_cap_per_day,
            remaining_today=remaining_after,
        ),
    )


@router.get("/competitions/{slug}/submissions/me", response_model=ApiEnvelope[list[SubmissionRead]])
def list_my_submissions(
    request: Request,
    slug: str,
    session: Session = Depends(get_session),
    exposure: Exposure = Depends(get_bound_exposure),
    user_id: UUID = Depends(get_current_user_id_checked),
    limit: int = 50,
    cursor: str | None = None,
) -> ApiEnvelope[list[SubmissionRead]]:
    limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)
    competition = competition_or_404(session, slug, exposure=exposure)
    submissions = list_submissions_for_user(
        session,
        competition_id=competition.id,
        user_id=user_id,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(submissions) > limit
    page = submissions[:limit]
    next_cursor = encode_offset_cursor(offset + limit) if has_more else None
    scores = load_official_scores_for_submissions(session, [submission.id for submission in page])
    return envelope(
        request,
        [
            submission_to_read(
                submission,
                competition_slug=competition.slug,
                official_score=scores.get(submission.id),
            )
            for submission in page
        ],
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )
