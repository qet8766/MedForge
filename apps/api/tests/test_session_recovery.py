from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.config import Settings
from app.models import Pack, SessionRecord, SessionStatus, Tier, User
from app.session_recovery import UNKNOWN_STATE_MAX_RETRIES, poll_active_sessions_once, reconcile_on_startup
from app.session_runtime import (
    ContainerInspection,
    MockSessionRuntime,
    RuntimeContainerState,
    SessionRuntimeError,
)


class RecoveryRuntime(MockSessionRuntime):
    def __init__(
        self,
        *,
        states: dict[str, RuntimeContainerState | list[RuntimeContainerState] | tuple[RuntimeContainerState, ...]]
        | None = None,
        snapshot_error: bool = False,
    ) -> None:
        self._states: dict[str, list[RuntimeContainerState]] = {}
        for key, raw in (states or {}).items():
            if isinstance(raw, RuntimeContainerState):
                self._states[key] = [raw]
            else:
                normalized = list(raw)
                if not normalized:
                    raise ValueError(f"State fixture for {key} cannot be empty.")
                self._states[key] = normalized
        self._snapshot_error = snapshot_error
        self.inspect_calls: dict[str, int] = {}

    def inspect_session_container(self, *, container_id: str | None, slug: str) -> ContainerInspection:
        key = container_id or f"mf-session-{slug}"
        self.inspect_calls[key] = self.inspect_calls.get(key, 0) + 1
        if key not in self._states:
            raise AssertionError(f"Missing state fixture for key={key}")
        sequence = self._states[key]
        state = sequence[0]
        if len(sequence) > 1:
            sequence.pop(0)
        resolved_container_id = None if state == RuntimeContainerState.MISSING else (container_id or key)
        return ContainerInspection(state=state, container_id=resolved_container_id)

    def snapshot_workspace(self, workspace_zfs: str, *, snapshot_name: str) -> None:
        _ = (workspace_zfs, snapshot_name)
        if self._snapshot_error:
            raise SessionRuntimeError("simulated snapshot failure")


def _insert_session_row(
    session: Session,
    *,
    status: SessionStatus,
    user_id: UUID,
    pack_id: UUID,
    gpu_id: int,
    container_id: str | None,
) -> SessionRecord:
    session_row = SessionRecord(
        user_id=user_id,
        tier=Tier.PUBLIC,
        pack_id=pack_id,
        status=status,
        container_id=container_id,
        gpu_id=gpu_id,
        gpu_active=1 if status in {SessionStatus.STARTING, SessionStatus.RUNNING, SessionStatus.STOPPING} else None,
        slug=uuid4().hex[:8],
        workspace_zfs=f"tank/medforge/workspaces/{user_id}/{uuid4()}",
    )
    session.add(session_row)
    session.commit()
    session.refresh(session_row)
    return session_row


def test_poll_active_sessions_normalizes_starting_to_running(db_engine, test_settings: Settings) -> None:
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="recover-starting@example.com", password_hash="x")
        session.add(user)
        session.commit()

        session_row = _insert_session_row(
            session,
            status=SessionStatus.STARTING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=0,
            container_id="poll-running-1",
        )

        runtime = RecoveryRuntime(states={"poll-running-1": RuntimeContainerState.RUNNING})
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(session_row)
        assert session_row.status == SessionStatus.RUNNING
        assert session_row.started_at is not None


def test_poll_active_sessions_marks_exited_container_error(db_engine, test_settings: Settings) -> None:
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="recover-exited@example.com", password_hash="x")
        session.add(user)
        session.commit()

        session_row = _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=1,
            container_id="poll-exited-1",
        )

        runtime = RecoveryRuntime(states={"poll-exited-1": RuntimeContainerState.EXITED})
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(session_row)
        assert session_row.status == SessionStatus.ERROR
        assert "container exited unexpectedly" in (session_row.error_message or "")


def test_poll_active_sessions_running_already_normalized_is_noop(db_engine, test_settings: Settings) -> None:
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="recover-running-noop@example.com", password_hash="x")
        session.add(user)
        session.commit()

        session_row = _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=2,
            container_id="poll-running-noop-1",
        )
        session_row.started_at = datetime.now(UTC)
        session.add(session_row)
        session.commit()
        session.refresh(session_row)
        initial_started_at = session_row.started_at

        runtime = RecoveryRuntime(states={"poll-running-noop-1": RuntimeContainerState.RUNNING})
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 0

        session.refresh(session_row)
        assert session_row.status == SessionStatus.RUNNING
        assert session_row.started_at == initial_started_at


def test_poll_active_sessions_unknown_state_retries_then_errors(db_engine, test_settings: Settings) -> None:
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="recover-unknown@example.com", password_hash="x")
        session.add(user)
        session.commit()

        session_row = _insert_session_row(
            session,
            status=SessionStatus.STARTING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=3,
            container_id="poll-unknown-1",
        )

        runtime = RecoveryRuntime(
            states={
                "poll-unknown-1": [
                    RuntimeContainerState.UNKNOWN,
                    RuntimeContainerState.UNKNOWN,
                ]
            }
        )
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 1
        assert runtime.inspect_calls["poll-unknown-1"] == UNKNOWN_STATE_MAX_RETRIES + 1

        session.refresh(session_row)
        assert session_row.status == SessionStatus.ERROR
        assert "unknown" in (session_row.error_message or "").lower()


def test_poll_active_sessions_handles_stop_race_without_clobbering_stopping(
    db_engine,
    test_settings: Settings,
) -> None:
    class PollStopRaceRuntime(MockSessionRuntime):
        def __init__(self, *, session_obj: Session, row: SessionRecord) -> None:
            self._session = session_obj
            self._row = row
            self._did_race = False

        def inspect_session_container(self, *, container_id: str | None, slug: str) -> ContainerInspection:
            _ = slug
            if not self._did_race:
                self._row.status = SessionStatus.STOPPING
                self._row.gpu_active = 1
                self._session.add(self._row)
                self._session.commit()
                self._session.refresh(self._row)
                self._did_race = True
            return ContainerInspection(state=RuntimeContainerState.EXITED, container_id=container_id)

    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="recover-race@example.com", password_hash="x")
        session.add(user)
        session.commit()

        session_row = _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=4,
            container_id="poll-race-1",
        )

        runtime = PollStopRaceRuntime(session_obj=session, row=session_row)
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 0

        session.refresh(session_row)
        assert session_row.status == SessionStatus.STOPPING


def test_reconcile_on_startup_terminalizes_starting_and_stopping(db_engine, test_settings: Settings) -> None:
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="recover-reconcile@example.com", password_hash="x")
        session.add(user)
        session.commit()

        starting_row = _insert_session_row(
            session,
            status=SessionStatus.STARTING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=2,
            container_id="startup-missing",
        )
        stopping_row = _insert_session_row(
            session,
            status=SessionStatus.STOPPING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=3,
            container_id="startup-stopping",
        )

        runtime = RecoveryRuntime(states={"startup-missing": RuntimeContainerState.MISSING})
        updated = reconcile_on_startup(session, settings=test_settings, runtime=runtime)
        assert updated == 2

        session.refresh(starting_row)
        session.refresh(stopping_row)
        assert starting_row.status == SessionStatus.ERROR
        assert starting_row.stopped_at is not None
        assert stopping_row.status == SessionStatus.STOPPED
        assert stopping_row.stopped_at is not None

        status_col = cast(Any, SessionRecord.status)
        stranded = session.exec(
            select(SessionRecord).where(status_col.in_((SessionStatus.STARTING, SessionStatus.STOPPING)))
        ).all()
        assert stranded == []


def test_reconcile_on_startup_running_session_unchanged_when_container_running(
    db_engine,
    test_settings: Settings,
) -> None:
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="recover-reconcile-running@example.com", password_hash="x")
        session.add(user)
        session.commit()

        running_row = _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=5,
            container_id="startup-running",
        )
        running_row.started_at = datetime.now(UTC)
        session.add(running_row)
        session.commit()
        session.refresh(running_row)
        initial_started_at = running_row.started_at

        runtime = RecoveryRuntime(states={"startup-running": RuntimeContainerState.RUNNING})
        updated = reconcile_on_startup(session, settings=test_settings, runtime=runtime)
        assert updated == 0

        session.refresh(running_row)
        assert running_row.status == SessionStatus.RUNNING
        assert running_row.started_at == initial_started_at


def test_reconcile_on_startup_snapshot_failure_marks_error(db_engine, test_settings: Settings) -> None:
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="recover-snapshot@example.com", password_hash="x")
        session.add(user)
        session.commit()

        stopping_row = _insert_session_row(
            session,
            status=SessionStatus.STOPPING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=4,
            container_id="startup-stopping-err",
        )

        runtime = RecoveryRuntime(snapshot_error=True)
        updated = reconcile_on_startup(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(stopping_row)
        assert stopping_row.status == SessionStatus.ERROR
        assert "snapshot failed" in (stopping_row.error_message or "")


def test_poll_and_reconcile_return_zero_with_no_active_sessions(db_engine, test_settings: Settings) -> None:
    with Session(db_engine) as session:
        runtime = RecoveryRuntime(states={})
        poll_updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        reconcile_updated = reconcile_on_startup(session, settings=test_settings, runtime=runtime)
        assert poll_updated == 0
        assert reconcile_updated == 0
