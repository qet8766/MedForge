"""MF-105: Chaos/failure injection tests.

Validates system self-healing when runtime operations fail:
- Stop errors: session remains in STOPPING, poller retries
- Snapshot errors: session marked ERROR with descriptive message
- Mixed failures: system converges to consistent state
"""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session, select

from app.config import Settings
from app.models import Pack, SessionStatus, User
from app.session_recovery import poll_active_sessions_once, reconcile_on_startup
from app.session_runtime import RuntimeContainerState
from tests.test_session_recovery import RecoveryRuntime, _insert_session_row


def test_stop_error_keeps_session_in_stopping(db_engine, test_settings: Settings) -> None:
    """When stop_session fails, poller leaves session as STOPPING for retry."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="chaos-stop@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.STOPPING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=0,
            container_id="chaos-stop-1",
        )

        runtime = RecoveryRuntime(stop_error=True)
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 0

        session.refresh(row)
        assert row.status == SessionStatus.STOPPING
        assert row.error_message is None


def test_snapshot_error_marks_session_error(db_engine, test_settings: Settings) -> None:
    """When snapshot_workspace fails after stop, session marked ERROR."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="chaos-snapshot@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.STOPPING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=1,
            container_id="chaos-snapshot-1",
        )

        runtime = RecoveryRuntime(snapshot_error=True)
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(row)
        assert row.status == SessionStatus.ERROR
        assert "snapshot failed" in (row.error_message or "")


def test_stop_then_snapshot_error_recovery_sequence(db_engine, test_settings: Settings) -> None:
    """First poll: stop fails (stays STOPPING). Second poll with fixed stop but
    broken snapshot: marks ERROR. System converges."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="chaos-sequence@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.STOPPING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=2,
            container_id="chaos-seq-1",
        )

        # Poll 1: stop fails
        runtime_fail = RecoveryRuntime(stop_error=True)
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime_fail)
        assert updated == 0
        session.refresh(row)
        assert row.status == SessionStatus.STOPPING

        # Poll 2: stop succeeds but snapshot fails
        runtime_snap = RecoveryRuntime(snapshot_error=True)
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime_snap)
        assert updated == 1
        session.refresh(row)
        assert row.status == SessionStatus.ERROR
        assert "snapshot failed" in (row.error_message or "")


def test_mixed_session_states_converge(db_engine, test_settings: Settings) -> None:
    """Multiple sessions in different states all converge to terminal."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="chaos-mixed@example.com", password_hash="x")
        session.add(user)
        session.commit()

        starting_row = _insert_session_row(
            session,
            status=SessionStatus.STARTING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=3,
            container_id="chaos-mixed-starting",
        )
        running_row = _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=4,
            container_id="chaos-mixed-running",
        )
        stopping_row = _insert_session_row(
            session,
            status=SessionStatus.STOPPING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=5,
            container_id="chaos-mixed-stopping",
        )

        runtime = RecoveryRuntime(
            states={
                "chaos-mixed-starting": RuntimeContainerState.MISSING,
                "chaos-mixed-running": RuntimeContainerState.EXITED,
            }
        )
        updated = reconcile_on_startup(session, settings=test_settings, runtime=runtime)
        assert updated == 3

        session.refresh(starting_row)
        session.refresh(running_row)
        session.refresh(stopping_row)

        assert starting_row.status == SessionStatus.ERROR
        assert running_row.status == SessionStatus.ERROR
        assert stopping_row.status == SessionStatus.STOPPED

        terminal_statuses = {SessionStatus.STOPPED, SessionStatus.ERROR}
        assert starting_row.status in terminal_statuses
        assert running_row.status in terminal_statuses
        assert stopping_row.status in terminal_statuses
