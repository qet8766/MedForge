from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.config import get_settings
from app.database import engine, init_db
from app.routers.auth import router as auth_router
from app.routers.competitions import router as competitions_router
from app.routers.control_plane import router as control_plane_router
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


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(competitions_router)
app.include_router(control_plane_router)


@app.get("/healthz")
def healthz(response: Response) -> dict[str, str]:
    if _is_session_recovery_healthy():
        return {"status": "ok"}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded"}
