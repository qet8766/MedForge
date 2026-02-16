"""MF-105: Post-load invariant assertions.

Validates system-wide invariants that must hold after any load test:
- No sessions stuck in STARTING
- GPU lock uniqueness holds
- All STOPPING sessions eventually resolve
"""
from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.config import Settings
from app.models import Pack, SessionRecord, SessionStatus, Tier, User
from app.session_recovery import poll_active_sessions_once, reconcile_on_startup
from app.session_repo import ACTIVE_SESSION_STATUSES
from app.session_runtime import RuntimeContainerState

from tests.test_session_recovery import RecoveryRuntime, _insert_session_row


def _count_by_status(session: Session, status: SessionStatus) -> int:
    """Count sessions in a given status."""
    count = session.exec(
        select(SessionRecord).where(SessionRecord.status == status)
    ).all()
    return len(count)


def _get_active_gpu_ids(session: Session) -> list[int]:
    """Get GPU IDs currently held by active sessions."""
    status_col = cast(Any, SessionRecord.status)
    rows = session.exec(
        select(SessionRecord).where(status_col.in_(ACTIVE_SESSION_STATUSES))
    ).all()
    return [r.gpu_id for r in rows]


def test_no_sessions_stuck_in_starting_after_reconcile(db_engine, test_settings: Settings) -> None:
    """After reconcile, no sessions should remain in STARTING state."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="inv-starting@example.com", password_hash="x")
        session.add(user)
        session.commit()

        for i in range(3):
            _insert_session_row(
                session,
                status=SessionStatus.STARTING,
                user_id=user.id,
                pack_id=pack.id,
                gpu_id=i,
                container_id=f"inv-start-{i}",
            )

        runtime = RecoveryRuntime(
            states={
                "inv-start-0": RuntimeContainerState.MISSING,
                "inv-start-1": RuntimeContainerState.RUNNING,
                "inv-start-2": RuntimeContainerState.EXITED,
            }
        )
        reconcile_on_startup(session, settings=test_settings, runtime=runtime)

        stuck = _count_by_status(session, SessionStatus.STARTING)
        assert stuck == 0, f"Found {stuck} sessions stuck in STARTING"


def test_gpu_lock_uniqueness_after_load(db_engine, test_settings: Settings) -> None:
    """Active GPU allocations must be unique — no two sessions share a GPU."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="inv-gpu@example.com", password_hash="x")
        session.add(user)
        session.commit()

        for i in range(5):
            _insert_session_row(
                session,
                status=SessionStatus.RUNNING,
                user_id=user.id,
                pack_id=pack.id,
                gpu_id=i,
                container_id=f"inv-gpu-{i}",
            )

        gpu_ids = _get_active_gpu_ids(session)
        assert len(gpu_ids) == len(set(gpu_ids)), (
            f"GPU uniqueness violated: {gpu_ids}"
        )


def test_all_stopping_resolved_after_reconcile(db_engine, test_settings: Settings) -> None:
    """After reconcile, no sessions should remain in STOPPING state."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="inv-stopping@example.com", password_hash="x")
        session.add(user)
        session.commit()

        for i in range(3):
            _insert_session_row(
                session,
                status=SessionStatus.STOPPING,
                user_id=user.id,
                pack_id=pack.id,
                gpu_id=i,
                container_id=f"inv-stop-{i}",
            )

        runtime = RecoveryRuntime(states={})
        reconcile_on_startup(session, settings=test_settings, runtime=runtime)

        stuck = _count_by_status(session, SessionStatus.STOPPING)
        assert stuck == 0, f"Found {stuck} sessions stuck in STOPPING"


def test_gpu_released_after_terminal_state(db_engine, test_settings: Settings) -> None:
    """After session reaches ERROR/STOPPED, its GPU must be freed."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="inv-release@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=6,
            container_id="inv-release-1",
        )

        runtime = RecoveryRuntime(states={"inv-release-1": RuntimeContainerState.EXITED})
        poll_active_sessions_once(session, settings=test_settings, runtime=runtime)

        session.refresh(row)
        assert row.status == SessionStatus.ERROR
        assert row.gpu_active is None, (
            f"GPU active hint not cleared: gpu_active={row.gpu_active}"
        )
