from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import structlog
from sqlalchemy import asc
from sqlmodel import Session, select

from app.config import Settings
from app.models import SessionRecord, SessionStatus
from app.session_repo import finalize_error, finalize_running, finalize_stopped
from app.session_runtime import (
    RuntimeContainerState,
    SessionRuntime,
    SessionRuntimeError,
    get_session_runtime,
)

logger = structlog.get_logger(__name__)

POLL_STATUSES: tuple[SessionStatus, ...] = (SessionStatus.STARTING, SessionStatus.RUNNING)
RECONCILE_STATUSES: tuple[SessionStatus, ...] = (
    SessionStatus.STARTING,
    SessionStatus.RUNNING,
    SessionStatus.STOPPING,
)


def _utc_millis() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _list_sessions_by_statuses(
    session: Session,
    *,
    statuses: tuple[SessionStatus, ...],
) -> list[SessionRecord]:
    status_col = cast(Any, SessionRecord.status)
    created_col = cast(Any, SessionRecord.created_at)
    statement = select(SessionRecord).where(status_col.in_(statuses)).order_by(asc(created_col))
    return list(session.exec(statement).all())


def _log_session_stop(row: SessionRecord, *, reason: str) -> None:
    logger.info(
        "session.stop",
        session_id=str(row.id),
        user_id=str(row.user_id),
        tier=row.tier.value,
        gpu_id=row.gpu_id,
        pack_id=str(row.pack_id),
        slug=row.slug,
        reason=reason,
    )


def _normalize_running(
    session: Session,
    *,
    row: SessionRecord,
    container_id: str | None,
) -> bool:
    resolved_container_id = container_id or row.container_id or f"mf-session-{row.slug}"
    if row.status == SessionStatus.RUNNING and row.container_id == resolved_container_id and row.started_at is not None:
        return False

    finalize_running(session, row=row, container_id=resolved_container_id)
    return True


def _mark_container_death(
    session: Session,
    *,
    row: SessionRecord,
    message: str,
) -> None:
    row = finalize_error(session, row=row, error_message=message)
    _log_session_stop(row, reason="container_death")


def complete_stopping_session(
    session: Session,
    *,
    row: SessionRecord,
    settings: Settings,
    runtime: SessionRuntime,
    success_reason: str = "user",
) -> SessionRecord:
    try:
        runtime.stop_session_container(
            row.container_id,
            timeout_seconds=settings.session_container_stop_timeout_seconds,
        )
        runtime.snapshot_workspace(
            row.workspace_zfs,
            snapshot_name=f"stop-{_utc_millis()}",
        )
        row = finalize_stopped(session, row=row)
        _log_session_stop(row, reason=success_reason)
        return row
    except Exception as exc:
        row = finalize_error(session, row=row, error_message=f"snapshot failed: {exc}")
        _log_session_stop(row, reason="snapshot_failed")
        return row


def _reconcile_active_row(
    session: Session,
    *,
    row: SessionRecord,
    runtime: SessionRuntime,
) -> bool:
    inspection = runtime.inspect_session_container(container_id=row.container_id, slug=row.slug)
    if inspection.state == RuntimeContainerState.RUNNING:
        return _normalize_running(session, row=row, container_id=inspection.container_id)

    if inspection.state == RuntimeContainerState.EXITED:
        _mark_container_death(session, row=row, message="container exited unexpectedly")
        return True

    if inspection.state == RuntimeContainerState.MISSING:
        _mark_container_death(session, row=row, message="container missing")
        return True

    return False


def poll_active_sessions_once(
    session: Session,
    *,
    settings: Settings,
    runtime: SessionRuntime | None = None,
) -> int:
    runtime = runtime or get_session_runtime(settings)
    rows = _list_sessions_by_statuses(session, statuses=POLL_STATUSES)
    updated = 0

    for row in rows:
        try:
            if _reconcile_active_row(session, row=row, runtime=runtime):
                updated += 1
        except SessionRuntimeError as exc:
            logger.warning("session.poll.inspect_failed", session_id=str(row.id), error=str(exc))

    return updated


def reconcile_on_startup(
    session: Session,
    *,
    settings: Settings,
    runtime: SessionRuntime | None = None,
) -> int:
    runtime = runtime or get_session_runtime(settings)
    rows = _list_sessions_by_statuses(session, statuses=RECONCILE_STATUSES)
    updated = 0

    for row in rows:
        if row.status == SessionStatus.STOPPING:
            complete_stopping_session(session, row=row, settings=settings, runtime=runtime)
            updated += 1
            continue

        try:
            changed = _reconcile_active_row(session, row=row, runtime=runtime)
        except SessionRuntimeError as exc:
            finalize_error(session, row=row, error_message=f"reconcile inspect failed: {exc}")
            updated += 1
            continue

        if changed:
            updated += 1
            continue

        if row.status == SessionStatus.STARTING:
            finalize_error(session, row=row, error_message="container not running during reconcile")
            updated += 1

    return updated
