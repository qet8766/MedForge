from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.problem_details import ProblemError, http_status_title, normalize_problem_type, problem_from_http_exception
from app.storage import SubmissionUploadTooLargeError

_PROBLEM_NAMESPACE = "competitions"


def _problem(
    *,
    status_code: int,
    type_slug: str,
    detail: str,
    title: str | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> ProblemError:
    return ProblemError(
        status_code=status_code,
        type=normalize_problem_type(f"{_PROBLEM_NAMESPACE}/{type_slug}"),
        title=title or http_status_title(status_code),
        detail=detail,
        errors=errors,
    )


def from_http_exception(exc: HTTPException, *, type_slug: str | None = None) -> ProblemError:
    if type_slug is None:
        return problem_from_http_exception(exc, problem_type=f"{_PROBLEM_NAMESPACE}/http-{exc.status_code}")
    return problem_from_http_exception(exc, problem_type=f"{_PROBLEM_NAMESPACE}/{type_slug}")


def competition_not_found(slug: str) -> ProblemError:
    return _problem(
        status_code=status.HTTP_404_NOT_FOUND,
        type_slug="competition-not-found",
        title="Competition Not Found",
        detail=f"Competition '{slug}' was not found.",
    )


def dataset_not_found(dataset_slug: str) -> ProblemError:
    return _problem(
        status_code=status.HTTP_404_NOT_FOUND,
        type_slug="dataset-not-found",
        title="Dataset Not Found",
        detail=f"Dataset '{dataset_slug}' was not found.",
    )


def submission_not_found(submission_id: UUID) -> ProblemError:
    return _problem(
        status_code=status.HTTP_404_NOT_FOUND,
        type_slug="submission-not-found",
        title="Submission Not Found",
        detail=f"Submission '{submission_id}' was not found.",
    )


def submission_too_large(exc: SubmissionUploadTooLargeError) -> ProblemError:
    return _problem(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        type_slug="submission-too-large",
        title="Submission File Too Large",
        detail=str(exc),
        errors=[
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
    )


def submission_validation_failed(detail: str) -> ProblemError:
    return _problem(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        type_slug="submission-validation-failed",
        title="Submission Validation Failed",
        detail=detail,
    )


def submission_processing_failed() -> ProblemError:
    return _problem(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        type_slug="submission-processing-failed",
        title="Submission Processing Failed",
        detail="An internal error occurred while processing the submission.",
    )


def competition_missing_for_submission(submission_id: UUID) -> ProblemError:
    return _problem(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        type_slug="competition-missing",
        title="Competition Missing",
        detail=f"Submission '{submission_id}' references a missing competition.",
    )


def corrupted_score_components(score_id: UUID) -> ProblemError:
    return _problem(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        type_slug="corrupted-score-components",
        title="Corrupted Score Components",
        detail=f"Submission score '{score_id}' has invalid score component data.",
    )


def dataset_path_outside_root(slug: str) -> ProblemError:
    return _problem(
        status_code=status.HTTP_403_FORBIDDEN,
        type_slug="dataset-path-outside-root",
        title="Path Outside Root",
        detail=f"Requested path is outside dataset '{slug}' root.",
    )
