"""MF-101: Poller SLA tests.

Validates that the session recovery poller detects and handles
container state anomalies within the configured poll interval.
"""
from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session, select

from app.config import Settings
from app.models import Pack, SessionStatus, User
from app.session_recovery import poll_active_sessions_once, reconcile_on_startup
from app.session_runtime import (
    RuntimeContainerState,
)
from tests.test_session_recovery import RecoveryRuntime, _insert_session_row


def test_poller_detects_unknown_state_within_configurable_retries(
    db_engine,
    test_settings: Settings,
) -> None:
    """Force UNKNOWN state → poller detects and marks ERROR after retries."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="poller-sla-unknown@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=0,
            container_id="sla-unknown-1",
        )

        runtime = RecoveryRuntime(
            states={"sla-unknown-1": RuntimeContainerState.UNKNOWN}
        )
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(row)
        assert row.status == SessionStatus.ERROR
        assert "unknown" in (row.error_message or "").lower()


def test_poller_transitions_exited_to_error(
    db_engine,
    test_settings: Settings,
) -> None:
    """Container exits unexpectedly → poller marks ERROR with snapshot attempt."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="poller-sla-exited@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=1,
            container_id="sla-exited-1",
        )

        runtime = RecoveryRuntime(states={"sla-exited-1": RuntimeContainerState.EXITED})
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(row)
        assert row.status == SessionStatus.ERROR
        assert row.stopped_at is not None
        assert "container exited unexpectedly" in (row.error_message or "")


def test_poller_recovers_unknown_to_running(
    db_engine,
    test_settings: Settings,
) -> None:
    """Transient UNKNOWN → RUNNING: poller normalizes without error."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="poller-sla-recover@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.STARTING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=2,
            container_id="sla-recover-1",
        )

        runtime = RecoveryRuntime(
            states={
                "sla-recover-1": [
                    RuntimeContainerState.UNKNOWN,
                    RuntimeContainerState.RUNNING,
                ]
            }
        )
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(row)
        assert row.status == SessionStatus.RUNNING
        assert row.started_at is not None


def test_reconcile_startup_handles_missing_containers(
    db_engine,
    test_settings: Settings,
) -> None:
    """Boot reconciliation marks STARTING with MISSING container as ERROR."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="poller-sla-missing@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.STARTING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=3,
            container_id="sla-missing-1",
        )

        runtime = RecoveryRuntime(states={"sla-missing-1": RuntimeContainerState.MISSING})
        updated = reconcile_on_startup(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(row)
        assert row.status == SessionStatus.ERROR
        assert row.stopped_at is not None


def test_poller_completes_stopping_session(
    db_engine,
    test_settings: Settings,
) -> None:
    """Stopping session with healthy runtime → poller completes stop + snapshot."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="poller-sla-stopping@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.STOPPING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=4,
            container_id="sla-stopping-1",
        )

        runtime = RecoveryRuntime(states={})
        updated = poll_active_sessions_once(session, settings=test_settings, runtime=runtime)
        assert updated == 1

        session.refresh(row)
        assert row.status == SessionStatus.STOPPED
        assert row.stopped_at is not None
        assert row.error_message is None
