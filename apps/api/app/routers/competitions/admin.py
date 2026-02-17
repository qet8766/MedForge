from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.api_contract import ApiEnvelope, envelope
from app.config import Settings, get_settings
from app.database import get_session
from app.models import Competition, CompetitionExposure, Exposure
from app.schemas import SubmissionRead
from app.services import process_submission_by_id

from .dependencies import get_bound_exposure, require_admin_access_checked, require_allowed_origin_checked
from .errors import competition_missing_for_submission, submission_not_found
from .mappers import submission_to_read
from .queries import load_official_scores_for_submissions

router = APIRouter()


@router.post("/admin/submissions/{submission_id}/score", response_model=ApiEnvelope[SubmissionRead])
def score_submission_once(
    request: Request,
    submission_id: UUID,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    exposure: Exposure = Depends(get_bound_exposure),
    _origin_guard: None = Depends(require_allowed_origin_checked),
    _admin: None = Depends(require_admin_access_checked),
) -> ApiEnvelope[SubmissionRead]:
    submission = process_submission_by_id(session, submission_id=submission_id, settings=settings)
    if submission is None:
        raise submission_not_found(submission_id)

    competition = session.get(Competition, submission.competition_id)
    if competition is None:
        raise competition_missing_for_submission(submission_id)
    if competition.competition_exposure != CompetitionExposure(exposure.value):
        raise submission_not_found(submission_id)

    official_score = load_official_scores_for_submissions(session, [submission.id]).get(submission.id)
    return envelope(
        request,
        submission_to_read(
            submission,
            competition_slug=competition.slug,
            official_score=official_score,
        ),
    )
