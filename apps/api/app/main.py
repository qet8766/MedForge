from __future__ import annotations

import threading

import structlog
from fastapi import FastAPI
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

app = FastAPI(title=settings.app_name)
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


def _session_recovery_loop() -> None:
    interval_seconds = settings.session_poll_interval_seconds
    while not _recovery_stop_event.is_set():
        try:
            with Session(engine) as session:
                updated = poll_active_sessions_once(session, settings=settings)
                if updated > 0:
                    logger.info("session.poll.updated", updated=updated)
        except Exception as exc:
            logger.warning("session.poll.failed", error=str(exc))

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


@app.on_event("startup")
def startup() -> None:
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


@app.on_event("shutdown")
def shutdown() -> None:
    global _recovery_thread
    if _recovery_thread is None:
        return
    _recovery_stop_event.set()
    _recovery_thread.join(timeout=5)
    _recovery_thread = None


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
