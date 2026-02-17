from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI

from app.problem_details import PROBLEM_CONTENT_TYPE, ProblemDocument, http_status_title

CANONICAL_API_PREFIX = "/api/v1"


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
    app.include_router(auth_router, prefix=CANONICAL_API_PREFIX)
    app.include_router(competitions_router, prefix=CANONICAL_API_PREFIX)
    app.include_router(control_plane_router, prefix=CANONICAL_API_PREFIX)
