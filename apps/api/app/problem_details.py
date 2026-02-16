from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.responses import Response

PROBLEM_CONTENT_TYPE = "application/problem+json"
PROBLEM_BASE_URI = "https://medforge.dev/problems"
log = logging.getLogger("medforge.problem_details")


@dataclass(slots=True)
class ProblemError(Exception):
    status_code: int
    type: str
    title: str
    detail: str
    code: str | None = None
    errors: list[dict[str, Any]] | None = None
    headers: dict[str, str] | None = None


class ProblemDocument(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: str
    errors: list[dict[str, Any]] | None = None


def normalize_problem_type(problem_type: str) -> str:
    if problem_type.startswith("http://") or problem_type.startswith("https://"):
        return problem_type
    return f"{PROBLEM_BASE_URI}/{problem_type.lstrip('/')}"


def normalize_problem_code(problem_code: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", problem_code.lower()).strip("_")


def http_status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Request Failed"


def _as_error_list(payload: Any) -> list[dict[str, Any]] | None:
    if not isinstance(payload, list):
        return None
    if not all(isinstance(item, dict) for item in payload):
        return None
    return [dict(item) for item in payload]


def coerce_detail(detail: Any) -> tuple[str, list[dict[str, Any]] | None]:
    if isinstance(detail, str):
        return detail, None

    if isinstance(detail, dict):
        nested_errors = _as_error_list(detail.get("errors"))
        message = detail.get("detail")
        if isinstance(message, str):
            return message, nested_errors
        if isinstance(message, list):
            errors = _as_error_list(message)
            if errors is not None:
                return "Request validation failed.", errors
        return "Request failed.", nested_errors

    list_errors = _as_error_list(detail)
    if list_errors is not None:
        return "Request validation failed.", list_errors

    return str(detail), None


def _code_from_type(problem_type: str) -> str:
    suffix = problem_type.rstrip("/").split("/")[-1]
    return normalize_problem_code(suffix.replace("-", "_")) or "request_failed"


def problem_from_http_exception(
    exc: HTTPException,
    *,
    problem_type: str | None = None,
    title: str | None = None,
    code: str | None = None,
) -> ProblemError:
    detail, errors = coerce_detail(exc.detail)
    normalized_type = normalize_problem_type(problem_type or f"http/{exc.status_code}")
    return ProblemError(
        status_code=exc.status_code,
        type=normalized_type,
        title=title or http_status_title(exc.status_code),
        detail=detail,
        code=code or _code_from_type(normalized_type),
        errors=errors,
        headers=cast(dict[str, str] | None, exc.headers),
    )


def build_problem_payload(*, problem: ProblemError, instance: str, request_id: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": problem.type,
        "title": problem.title,
        "status": problem.status_code,
        "detail": problem.detail,
        "instance": instance,
        "code": problem.code or _code_from_type(problem.type),
        "request_id": request_id,
    }
    if problem.errors is not None:
        payload["errors"] = problem.errors
    return payload


async def problem_error_handler(request: Request, exc: ProblemError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    payload = build_problem_payload(
        problem=exc,
        instance=request.url.path,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        media_type=PROBLEM_CONTENT_TYPE,
        headers=exc.headers,
    )


def register_problem_exception_handler(app: FastAPI) -> None:
    problem_handler = cast(
        Callable[[Request, Exception], Response | Awaitable[Response]],
        problem_error_handler,
    )
    app.add_exception_handler(ProblemError, problem_handler)

    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return await problem_error_handler(request, problem_from_http_exception(exc))

    async def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        problem = ProblemError(
            status_code=422,
            type=normalize_problem_type("validation/request"),
            title="Request Validation Failed",
            detail="Request validation failed.",
            code="request_validation_failed",
            errors=[dict(item) for item in exc.errors()],
        )
        return await problem_error_handler(request, problem)

    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_api_error", exc_info=exc)
        problem = ProblemError(
            status_code=500,
            type=normalize_problem_type("http/500"),
            title=http_status_title(500),
            detail="An unexpected internal server error occurred.",
            code="http_500",
        )
        return await problem_error_handler(request, problem)

    app.add_exception_handler(HTTPException, cast(Any, _http_exception_handler))
    app.add_exception_handler(RequestValidationError, cast(Any, _validation_exception_handler))
    app.add_exception_handler(Exception, cast(Any, _unhandled_exception_handler))


# ── Error code registry ─────────────────────────────────────────────
# Centralized mapping from error code → (HTTP status, problem type).
# Used for consistent error responses across the API.

ERROR_CODE_REGISTRY: dict[str, tuple[int, str]] = {
    "rate_limit_exceeded": (429, "rate-limit/exceeded"),
    "request_validation_failed": (422, "validation/request"),
    "submission_cap_reached": (429, "competitions/submission-cap-reached"),
    "submission_validation_failed": (422, "competitions/submission-validation-failed"),
    "submission_too_large": (422, "competitions/submission-too-large"),
    "submission_not_found": (404, "competitions/submission-not-found"),
    "submission_processing_failed": (500, "competitions/submission-processing-failed"),
    "competition_not_found": (404, "competitions/competition-not-found"),
    "dataset_not_found": (404, "competitions/dataset-not-found"),
    "origin_not_allowed": (403, "competitions/origin-not-allowed"),
    "admin_access_denied": (403, "competitions/admin-access-denied"),
    "pagination_invalid_limit": (400, "pagination/invalid-limit"),
    "pagination_invalid_cursor": (400, "pagination/invalid-cursor"),
    "http_400": (400, "http/400"),
    "http_401": (401, "http/401"),
    "http_403": (403, "http/403"),
    "http_404": (404, "http/404"),
    "http_409": (409, "http/409"),
    "http_500": (500, "http/500"),
    "http_501": (501, "http/501"),
    "http_503": (503, "http/503"),
}


def problem_from_code(
    code: str,
    *,
    detail: str,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> ProblemError:
    """Create a ProblemError from a registered error code."""
    entry = ERROR_CODE_REGISTRY.get(code)
    if entry is None:
        status_code = 500
        problem_type = normalize_problem_type(f"http/{status_code}")
    else:
        status_code, type_suffix = entry
        problem_type = normalize_problem_type(type_suffix)

    return ProblemError(
        status_code=status_code,
        type=problem_type,
        title=http_status_title(status_code),
        detail=detail,
        code=code,
        errors=errors,
        headers=headers,
    )
