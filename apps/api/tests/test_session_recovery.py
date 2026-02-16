from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.config import Settings
from app.models import Pack, SessionRecord, SessionStatus, Tier, User
from app.session_recovery import poll_active_sessions_once, reconcile_on_startup
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
        states: dict[str, RuntimeContainerState] | None = None,
        snapshot_error: bool = False,
    ) -> None:
        self._states = states or {}
        self._snapshot_error = snapshot_error

    def inspect_session_container(self, *, container_id: str | None, slug: str) -> ContainerInspection:
        key = container_id or f"mf-session-{slug}"
        state = self._states.get(key, RuntimeContainerState.RUNNING)
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
