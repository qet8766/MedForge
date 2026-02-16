from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

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
ACTIVE_MUTATION_STATUSES: tuple[SessionStatus, ...] = (SessionStatus.STARTING, SessionStatus.RUNNING)
UNKNOWN_STATE_MAX_RETRIES = 3
UNKNOWN_STATE_RETRY_DELAY_SECONDS = 0.25


def _utc_millis() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _is_sqlite(session: Session) -> bool:
    bind = session.get_bind()
    return bind.dialect.name == "sqlite"


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


def _get_row_for_update(
    session: Session,
    *,
    row_id: UUID,
) -> SessionRecord | None:
    statement = select(SessionRecord).where(SessionRecord.id == row_id)
    if not _is_sqlite(session):
        statement = statement.with_for_update()
    return session.exec(statement).first()


def _lock_row_for_mutation(
    session: Session,
    *,
    row: SessionRecord,
    expected_statuses: tuple[SessionStatus, ...],
    mutation: str,
) -> SessionRecord | None:
    locked_row = _get_row_for_update(session, row_id=row.id)
    if locked_row is None:
        logger.info(
            "session.recovery.mutation_skipped",
            session_id=str(row.id),
            user_id=str(row.user_id),
            slug=row.slug,
            mutation=mutation,
            reason="row_missing",
        )
        return None
    if locked_row.status not in expected_statuses:
        logger.info(
            "session.recovery.mutation_skipped",
            session_id=str(locked_row.id),
            user_id=str(locked_row.user_id),
            slug=locked_row.slug,
            mutation=mutation,
            reason="stale_status",
            status=locked_row.status.value,
        )
        return None
    return locked_row


def _refresh_row(session: Session, *, row: SessionRecord) -> SessionRecord:
    current = session.get(SessionRecord, row.id)
    if current is None:
        return row
    return current


def _normalize_running(
    session: Session,
    *,
    row: SessionRecord,
    container_id: str | None,
) -> bool:
    resolved_container_id = container_id or row.container_id
    if resolved_container_id is None:
        logger.warning(
            "session.recovery.running_without_container_id",
            session_id=str(row.id),
            user_id=str(row.user_id),
            slug=row.slug,
        )
        return False
    if row.status == SessionStatus.RUNNING and row.container_id == resolved_container_id and row.started_at is not None:
        return False

    finalize_running(session, row=row, container_id=resolved_container_id)
    return True


def _mark_container_death(
    session: Session,
    *,
    row: SessionRecord,
    settings: Settings,
    runtime: SessionRuntime,
    container_id: str | None,
    message: str,
) -> bool:
    locked_row = _lock_row_for_mutation(
        session,
        row=row,
        expected_statuses=ACTIVE_MUTATION_STATUSES,
        mutation="container_death",
    )
    if locked_row is None:
        return False

    cleanup_container_id = container_id or locked_row.container_id
    try:
        runtime.stop_session_container(
            cleanup_container_id,
            timeout_seconds=settings.session_container_stop_timeout_seconds,
        )
    except Exception as exc:
        logger.warning(
            "session.container_death.cleanup_failed",
            session_id=str(locked_row.id),
            user_id=str(locked_row.user_id),
            slug=locked_row.slug,
            container_id=cleanup_container_id,
            error=str(exc),
        )

    snapshot_error: Exception | None = None
    try:
        runtime.snapshot_workspace(
            locked_row.workspace_zfs,
            snapshot_name=f"death-{_utc_millis()}",
        )
    except Exception as exc:
        snapshot_error = exc
        logger.warning(
            "session.container_death.snapshot_failed",
            session_id=str(locked_row.id),
            user_id=str(locked_row.user_id),
            slug=locked_row.slug,
            error=str(exc),
        )

    error_message = message if snapshot_error is None else f"{message}; snapshot failed: {snapshot_error}"
    row = finalize_error(session, row=locked_row, error_message=error_message)
    _log_session_stop(row, reason="container_death")
    return True


def _inspect_with_unknown_retries(
    *,
    row: SessionRecord,
    runtime: SessionRuntime,
) -> tuple[RuntimeContainerState, str | None]:
    inspection = runtime.inspect_session_container(container_id=row.container_id, slug=row.slug)
    retries = 0

    while inspection.state == RuntimeContainerState.UNKNOWN and retries < UNKNOWN_STATE_MAX_RETRIES:
        retries += 1
        logger.warning(
            "session.inspect.unknown_retry",
            session_id=str(row.id),
            user_id=str(row.user_id),
            slug=row.slug,
            retry=retries,
            max_retries=UNKNOWN_STATE_MAX_RETRIES,
        )
        time.sleep(UNKNOWN_STATE_RETRY_DELAY_SECONDS)
        inspection = runtime.inspect_session_container(container_id=row.container_id, slug=row.slug)

    return inspection.state, inspection.container_id


def _mark_unknown_state_error(
    session: Session,
    *,
    row: SessionRecord,
) -> bool:
    locked_row = _lock_row_for_mutation(
        session,
        row=row,
        expected_statuses=ACTIVE_MUTATION_STATUSES,
        mutation="unknown_state",
    )
    if locked_row is None:
        return False

    finalized = finalize_error(
        session,
        row=locked_row,
        error_message=f"container state unknown after {UNKNOWN_STATE_MAX_RETRIES} retries",
    )
    _log_session_stop(finalized, reason="container_state_unknown")
    return True


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
        locked_row = _lock_row_for_mutation(
            session,
            row=row,
            expected_statuses=(SessionStatus.STOPPING,),
            mutation="finalize_stopped",
        )
        if locked_row is None:
            return _refresh_row(session, row=row)
        row = finalize_stopped(session, row=locked_row)
        _log_session_stop(row, reason=success_reason)
        return row
    except Exception as exc:
        locked_row = _lock_row_for_mutation(
            session,
            row=row,
            expected_statuses=(SessionStatus.STOPPING,),
            mutation="finalize_stopping_error",
        )
        if locked_row is None:
            return _refresh_row(session, row=row)
        row = finalize_error(session, row=locked_row, error_message=f"snapshot failed: {exc}")
        _log_session_stop(row, reason="snapshot_failed")
        return row


def _reconcile_active_row(
    session: Session,
    *,
    row: SessionRecord,
    settings: Settings,
    runtime: SessionRuntime,
) -> bool:
    state, resolved_container_id = _inspect_with_unknown_retries(row=row, runtime=runtime)
    if state == RuntimeContainerState.RUNNING:
        locked_row = _lock_row_for_mutation(
            session,
            row=row,
            expected_statuses=ACTIVE_MUTATION_STATUSES,
            mutation="normalize_running",
        )
        if locked_row is None:
            return False
        return _normalize_running(session, row=locked_row, container_id=resolved_container_id)

    if state == RuntimeContainerState.EXITED:
        return _mark_container_death(
            session,
            row=row,
            settings=settings,
            runtime=runtime,
            container_id=resolved_container_id,
            message="container exited unexpectedly",
        )

    if state == RuntimeContainerState.MISSING:
        return _mark_container_death(
            session,
            row=row,
            settings=settings,
            runtime=runtime,
            container_id=resolved_container_id,
            message="container missing",
        )

    if state == RuntimeContainerState.UNKNOWN:
        return _mark_unknown_state_error(session, row=row)

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
            if _reconcile_active_row(session, row=row, settings=settings, runtime=runtime):
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
            stopping_row = complete_stopping_session(session, row=row, settings=settings, runtime=runtime)
            if stopping_row.status in {SessionStatus.STOPPED, SessionStatus.ERROR}:
                updated += 1
            continue

        try:
            changed = _reconcile_active_row(session, row=row, settings=settings, runtime=runtime)
        except SessionRuntimeError as exc:
            locked_row = _lock_row_for_mutation(
                session,
                row=row,
                expected_statuses=ACTIVE_MUTATION_STATUSES,
                mutation="reconcile_inspect_error",
            )
            if locked_row is not None:
                finalize_error(session, row=locked_row, error_message=f"reconcile inspect failed: {exc}")
                updated += 1
            continue

        if changed:
            updated += 1
            continue

        if row.status == SessionStatus.STARTING:
            locked_row = _lock_row_for_mutation(
                session,
                row=row,
                expected_statuses=(SessionStatus.STARTING,),
                mutation="reconcile_starting_not_running",
            )
            if locked_row is not None:
                finalize_error(session, row=locked_row, error_message="container not running during reconcile")
                updated += 1

    return updated
