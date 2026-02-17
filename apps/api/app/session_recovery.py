from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import structlog
from sqlalchemy import asc
from sqlmodel import Session, select

from app.config import Settings
from app.models import SessionRecord, SessionStatus
from app.session_repo import finalize_error, finalize_running, finalize_stopped
from app.session_runtime import (
    RuntimeContainerState,
    SessionInspectRequest,
    SessionRuntime,
    SessionRuntimeError,
    SessionStopRequest,
    WorkspaceSnapshotRequest,
    get_session_runtime,
)

logger = structlog.get_logger(__name__)

POLL_STATUSES: tuple[SessionStatus, ...] = (
    SessionStatus.STARTING,
    SessionStatus.RUNNING,
    SessionStatus.STOPPING,
)
ACTIVE_MUTATION_STATUSES: tuple[SessionStatus, ...] = (SessionStatus.STARTING, SessionStatus.RUNNING)
UNKNOWN_STATE_MAX_RETRIES = 3
UNKNOWN_STATE_RETRY_DELAY_SECONDS = 0.25


def _utc_millis() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _list_sessions_by_statuses(session: Session, *, statuses: tuple[SessionStatus, ...]) -> list[SessionRecord]:
    status_col = cast(Any, SessionRecord.status)
    created_col = cast(Any, SessionRecord.created_at)
    statement = select(SessionRecord).where(status_col.in_(statuses)).order_by(asc(created_col))
    return list(session.exec(statement).all())


def _log_session_stop(row: SessionRecord, *, reason: str) -> None:
    logger.info(
        "session.stop",
        session_id=str(row.id),
        user_id=str(row.user_id),
        exposure=row.exposure.value,
        gpu_id=row.gpu_id,
        pack_id=str(row.pack_id),
        slug=row.slug,
        reason=reason,
    )


def _get_row_for_update(session: Session, *, row_id: UUID) -> SessionRecord | None:
    statement = select(SessionRecord).where(SessionRecord.id == row_id).with_for_update()
    return session.exec(statement).first()


class SessionRecoveryRunner:
    def __init__(self, *, session: Session, settings: Settings, runtime: SessionRuntime) -> None:
        self._session = session
        self._settings = settings
        self._runtime = runtime

    def poll_active_once(self) -> int:
        return self._run_once(startup=False)

    def reconcile_startup_once(self) -> int:
        return self._run_once(startup=True)

    def _run_once(self, *, startup: bool) -> int:
        correlation_id = str(uuid4())
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            recovery_mode="startup" if startup else "poll",
        )
        updated = 0
        rows = _list_sessions_by_statuses(self._session, statuses=POLL_STATUSES)
        for row in rows:
            if row.status == SessionStatus.STOPPING:
                if self._complete_stopping_session(row=row):
                    updated += 1
                continue

            try:
                changed = self._reconcile_active_row(row=row)
            except SessionRuntimeError as exc:
                if startup:
                    if self._finalize_error(
                        row=row,
                        expected_statuses=ACTIVE_MUTATION_STATUSES,
                        mutation="reconcile_inspect_error",
                        error_message=f"reconcile inspect failed: {exc}",
                    ):
                        updated += 1
                else:
                    logger.warning("session.poll.inspect_failed", session_id=str(row.id), error=str(exc))
                continue

            if changed:
                updated += 1
                continue

            if startup and row.status == SessionStatus.STARTING and self._finalize_error(
                row=row,
                expected_statuses=(SessionStatus.STARTING,),
                mutation="reconcile_starting_not_running",
                error_message="container not running during reconcile",
            ):
                updated += 1

        return updated

    def _complete_stopping_session(self, *, row: SessionRecord) -> bool:
        try:
            self._runtime.stop_session(
                SessionStopRequest(
                    container_id=row.container_id,
                    timeout_seconds=self._settings.session_container_stop_timeout_seconds,
                )
            )
        except Exception as exc:
            logger.warning(
                "session.recovery.failure",
                session_id=str(row.id),
                user_id=str(row.user_id),
                slug=row.slug,
                mutation="complete_stopping_session",
                operation="stop_session",
                error_code="stop_failed",
                error=str(exc),
            )
            return False

        snapshot_error: Exception | None = None
        try:
            self._runtime.snapshot_workspace(
                WorkspaceSnapshotRequest(
                    workspace_zfs=row.workspace_zfs,
                    snapshot_name=f"stop-{_utc_millis()}",
                )
            )
        except Exception as exc:
            snapshot_error = exc
            logger.warning(
                "session.recovery.failure",
                session_id=str(row.id),
                user_id=str(row.user_id),
                slug=row.slug,
                mutation="complete_stopping_session",
                operation="snapshot_workspace",
                error_code="snapshot_failed",
                error=str(exc),
            )

        if snapshot_error is not None:
            return self._finalize_error(
                row=row,
                expected_statuses=(SessionStatus.STOPPING,),
                mutation="finalize_stopping_error",
                error_message=f"snapshot failed: {snapshot_error}",
                stop_reason="snapshot_failed",
            )

        locked = self._lock_row_for_mutation(
            row=row,
            expected_statuses=(SessionStatus.STOPPING,),
            mutation="finalize_stopped",
        )
        if locked is None:
            return False

        finalized = finalize_stopped(self._session, row=locked)
        _log_session_stop(finalized, reason="requested")
        return True

    def _reconcile_active_row(self, *, row: SessionRecord) -> bool:
        state, container_id = self._inspect_state(row=row)
        logger.info(
            "session.recovery.decision",
            session_id=str(row.id),
            user_id=str(row.user_id),
            slug=row.slug,
            state=state.value,
            container_id=container_id,
        )

        if state == RuntimeContainerState.RUNNING:
            locked = self._lock_row_for_mutation(
                row=row,
                expected_statuses=ACTIVE_MUTATION_STATUSES,
                mutation="normalize_running",
            )
            if locked is None:
                return False
            return self._normalize_running(row=locked, container_id=container_id)

        if state in {RuntimeContainerState.EXITED, RuntimeContainerState.MISSING}:
            message = "container exited unexpectedly" if state == RuntimeContainerState.EXITED else "container missing"
            return self._mark_container_not_running(
                row=row,
                container_id=container_id,
                message=message,
            )

        if state == RuntimeContainerState.UNKNOWN:
            return self._finalize_error(
                row=row,
                expected_statuses=ACTIVE_MUTATION_STATUSES,
                mutation="unknown_state",
                error_message=f"container state unknown after {UNKNOWN_STATE_MAX_RETRIES} retries",
                stop_reason="container_state_unknown",
            )

        return False

    def _inspect_state(self, *, row: SessionRecord) -> tuple[RuntimeContainerState, str | None]:
        inspection = self._runtime.inspect_session(
            SessionInspectRequest(container_id=row.container_id, slug=row.slug)
        )
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
            inspection = self._runtime.inspect_session(
                SessionInspectRequest(container_id=row.container_id, slug=row.slug)
            )
        return inspection.state, inspection.container_id

    def _mark_container_not_running(
        self,
        *,
        row: SessionRecord,
        container_id: str | None,
        message: str,
    ) -> bool:
        locked = self._lock_row_for_mutation(
            row=row,
            expected_statuses=ACTIVE_MUTATION_STATUSES,
            mutation="container_not_running",
        )
        if locked is None:
            return False

        cleanup_container_id = container_id or locked.container_id
        try:
            self._runtime.stop_session(
                SessionStopRequest(
                    container_id=cleanup_container_id,
                    timeout_seconds=self._settings.session_container_stop_timeout_seconds,
                )
            )
        except Exception as exc:
            logger.warning(
                "session.container_death.cleanup_failed",
                session_id=str(locked.id),
                user_id=str(locked.user_id),
                slug=locked.slug,
                container_id=cleanup_container_id,
                error=str(exc),
            )

        snapshot_error: Exception | None = None
        try:
            self._runtime.snapshot_workspace(
                WorkspaceSnapshotRequest(
                    workspace_zfs=locked.workspace_zfs,
                    snapshot_name=f"death-{_utc_millis()}",
                )
            )
        except Exception as exc:
            snapshot_error = exc
            logger.warning(
                "session.container_death.snapshot_failed",
                session_id=str(locked.id),
                user_id=str(locked.user_id),
                slug=locked.slug,
                error=str(exc),
            )

        final_message = message if snapshot_error is None else f"{message}; snapshot failed: {snapshot_error}"
        finalized = finalize_error(self._session, row=locked, error_message=final_message)
        _log_session_stop(finalized, reason="container_death")
        return True

    def _normalize_running(self, *, row: SessionRecord, container_id: str | None) -> bool:
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

        finalize_running(self._session, row=row, container_id=resolved_container_id)
        return True

    def _finalize_error(
        self,
        *,
        row: SessionRecord,
        expected_statuses: tuple[SessionStatus, ...],
        mutation: str,
        error_message: str,
        stop_reason: str | None = None,
    ) -> bool:
        locked = self._lock_row_for_mutation(
            row=row,
            expected_statuses=expected_statuses,
            mutation=mutation,
        )
        if locked is None:
            return False

        finalized = finalize_error(self._session, row=locked, error_message=error_message)
        if stop_reason is not None:
            _log_session_stop(finalized, reason=stop_reason)
        return True

    def _lock_row_for_mutation(
        self,
        *,
        row: SessionRecord,
        expected_statuses: tuple[SessionStatus, ...],
        mutation: str,
    ) -> SessionRecord | None:
        locked = _get_row_for_update(self._session, row_id=row.id)
        if locked is None:
            logger.info(
                "session.recovery.mutation_skipped",
                session_id=str(row.id),
                user_id=str(row.user_id),
                slug=row.slug,
                mutation=mutation,
                reason="row_missing",
            )
            return None
        if locked.status not in expected_statuses:
            logger.info(
                "session.recovery.mutation_skipped",
                session_id=str(locked.id),
                user_id=str(locked.user_id),
                slug=locked.slug,
                mutation=mutation,
                reason="stale_status",
                status=locked.status.value,
            )
            return None
        return locked


def poll_active_sessions_once(
    session: Session,
    *,
    settings: Settings,
    runtime: SessionRuntime | None = None,
) -> int:
    recovery_runtime = runtime or get_session_runtime(settings)
    runner = SessionRecoveryRunner(session=session, settings=settings, runtime=recovery_runtime)
    return runner.poll_active_once()


def reconcile_on_startup(
    session: Session,
    *,
    settings: Settings,
    runtime: SessionRuntime | None = None,
) -> int:
    recovery_runtime = runtime or get_session_runtime(settings)
    runner = SessionRecoveryRunner(session=session, settings=settings, runtime=recovery_runtime)
    return runner.reconcile_startup_once()
