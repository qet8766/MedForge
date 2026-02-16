from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI
from starlette.responses import Response

from app.config import Settings
from app.problem_details import PROBLEM_CONTENT_TYPE, ProblemDocument, http_status_title

CANONICAL_API_PREFIX = "/api/v1"
LEGACY_API_PREFIX = "/api"


def default_problem_responses() -> dict[int | str, dict[str, Any]]:
    statuses = (400, 401, 403, 404, 409, 422, 429, 500, 501, 503)
    problem_schema = ProblemDocument.model_json_schema()
    return {
        code: {
            "description": http_status_title(code),
            "content": {
                PROBLEM_CONTENT_TYPE: {
                    "schema": problem_schema,
                }
            },
        }
        for code in statuses
    }


def include_api_routers(
    app: FastAPI,
    *,
    auth_router: APIRouter,
    competitions_router: APIRouter,
    control_plane_router: APIRouter,
) -> None:
    for prefix in (CANONICAL_API_PREFIX, LEGACY_API_PREFIX):
        app.include_router(auth_router, prefix=prefix)
        app.include_router(competitions_router, prefix=prefix)
        app.include_router(control_plane_router, prefix=prefix)


def is_legacy_api_path(path: str) -> bool:
    if path == LEGACY_API_PREFIX:
        return True
    if not path.startswith(f"{LEGACY_API_PREFIX}/"):
        return False
    return not path.startswith(f"{CANONICAL_API_PREFIX}/")


def apply_legacy_api_deprecation_headers(response: Response, *, settings: Settings) -> None:
    if not settings.legacy_api_deprecation_enabled:
        return
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = settings.legacy_api_sunset
    response.headers["Link"] = f'<{settings.legacy_api_deprecation_link}>; rel="deprecation"'
