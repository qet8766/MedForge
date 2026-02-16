from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from app.models import ScoreStatus, Submission
from app.storage import StoredFile


def create_queued_submission(
    session: Session,
    *,
    competition_id: UUID,
    user_id: UUID,
    filename: str,
) -> Submission:
    submission = Submission(
        competition_id=competition_id,
        user_id=user_id,
        filename=filename,
        artifact_path="",
        artifact_sha256="",
        row_count=0,
        score_status=ScoreStatus.QUEUED,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission


def persist_stored_submission(session: Session, *, submission: Submission, stored: StoredFile) -> Submission:
    submission.artifact_path = str(stored.path)
    submission.artifact_sha256 = stored.sha256
    submission.row_count = stored.row_count
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission


def mark_submission_failed(session: Session, *, submission: Submission, error: str) -> Submission:
    submission.score_status = ScoreStatus.FAILED
    submission.score_error = error
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission
