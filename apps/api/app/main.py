from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from starlette.middleware.base import RequestResponseEndpoint

from app.api_contract import ApiEnvelope, envelope
from app.config import get_settings
from app.database import engine, init_db
from app.http_contract import (
    default_problem_responses,
    include_api_routers,
)
from app.problem_details import register_problem_exception_handler
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.competitions import router as competitions_router
from app.routers.control_plane import router as control_plane_router
from app.schemas import HealthResponse
from app.seed import seed_defaults
from app.session_recovery import poll_active_sessions_once, reconcile_on_startup

settings = get_settings()
logger = structlog.get_logger(__name__)
_recovery_stop_event = threading.Event()
_recovery_thread: threading.Thread | None = None


def _session_recovery_loop() -> None:
    base_interval_seconds = settings.session_poll_interval_seconds
    backoff_cap_seconds = max(settings.session_poll_backoff_max_seconds, base_interval_seconds)
    interval_seconds = base_interval_seconds
    consecutive_failures = 0
    while not _recovery_stop_event.is_set():
        try:
            with Session(engine) as session:
                updated = poll_active_sessions_once(session, settings=settings)
                if updated > 0:
                    logger.info("session.poll.updated", updated=updated)
            consecutive_failures = 0
            interval_seconds = base_interval_seconds
        except Exception as exc:
            consecutive_failures += 1
            interval_seconds = min(interval_seconds * 2, backoff_cap_seconds)
            logger.warning(
                "session.poll.failed",
                error=str(exc),
                consecutive_failures=consecutive_failures,
                next_poll_seconds=interval_seconds,
            )

        if _recovery_stop_event.wait(interval_seconds):
            break


def _start_session_recovery_thread() -> None:
    global _recovery_thread
    if _recovery_thread is not None and _recovery_thread.is_alive():
        return
    _recovery_stop_event.clear()
    _recovery_thread = threading.Thread(
        target=_session_recovery_loop,
        name="medforge-session-recovery",
        daemon=True,
    )
    _recovery_thread.start()


def _stop_session_recovery_thread() -> None:
    global _recovery_thread
    if _recovery_thread is None:
        return
    _recovery_stop_event.set()
    _recovery_thread.join(timeout=5)
    _recovery_thread = None


def _is_session_recovery_healthy() -> bool:
    if not settings.session_recovery_enabled:
        return True
    return _recovery_thread is not None and _recovery_thread.is_alive()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    with Session(engine) as session:
        seed_defaults(session)

    if settings.session_recovery_enabled:
        try:
            with Session(engine) as session:
                updated = reconcile_on_startup(session, settings=settings)
                if updated > 0:
                    logger.info("session.reconcile.updated", updated=updated)
        except Exception as exc:
            logger.warning("session.reconcile.failed", error=str(exc))
        _start_session_recovery_thread()
    try:
        yield
    finally:
        _stop_session_recovery_thread()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    responses=default_problem_responses(),
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)
include_api_routers(
    app,
    auth_router=auth_router,
    competitions_router=competitions_router,
    control_plane_router=control_plane_router,
    admin_router=admin_router,
)
register_problem_exception_handler(app)


@app.middleware("http")
async def request_contract_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request_id = str(uuid4())
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/healthz", response_model=ApiEnvelope[HealthResponse])
def healthz(request: Request, response: Response) -> ApiEnvelope[HealthResponse]:
    if _is_session_recovery_healthy():
        return envelope(request, HealthResponse(status="ok"))

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return envelope(request, HealthResponse(status="degraded"))
