"""MF-103: Log schema validation tests.

Validates that lifecycle log events contain required context fields
for multi-tenant debugging: session_id, user_id, event name.
"""
from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session, select

from app.config import Settings
from app.models import Pack, SessionStatus, User
from app.session_recovery import poll_active_sessions_once
from app.session_runtime import RuntimeContainerState
from tests.test_session_recovery import RecoveryRuntime, _insert_session_row


def test_poll_log_contains_session_and_user_ids(db_engine, test_settings: Settings, capsys) -> None:
    """Poll events must include session_id and user_id for traceability."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="log-schema@example.com", password_hash="x")
        session.add(user)
        session.commit()

        row = _insert_session_row(
            session,
            status=SessionStatus.STARTING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=0,
            container_id="log-schema-1",
        )

        runtime = RecoveryRuntime(states={"log-schema-1": RuntimeContainerState.RUNNING})
        poll_active_sessions_once(session, settings=test_settings, runtime=runtime)

        captured = capsys.readouterr()
        log_output = captured.out + captured.err

        assert "session_id" in log_output or str(row.id) in log_output, (
            f"Log output missing session_id. Got: {log_output!r}"
        )
        assert "user_id" in log_output or str(user.id) in log_output, (
            f"Log output missing user_id. Got: {log_output!r}"
        )


def test_session_stop_log_contains_required_fields(db_engine, test_settings: Settings, capsys) -> None:
    """Session stop events must include session context fields."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="log-stop@example.com", password_hash="x")
        session.add(user)
        session.commit()

        _insert_session_row(
            session,
            status=SessionStatus.RUNNING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=1,
            container_id="log-stop-1",
        )

        runtime = RecoveryRuntime(states={"log-stop-1": RuntimeContainerState.EXITED})
        poll_active_sessions_once(session, settings=test_settings, runtime=runtime)

        captured = capsys.readouterr()
        log_output = captured.out + captured.err

        assert "session.stop" in log_output or "session.recovery" in log_output, (
            f"Expected lifecycle event in logs. Got: {log_output!r}"
        )
        assert str(user.id) in log_output, (
            f"Log output missing user_id. Got: {log_output!r}"
        )


def test_recovery_failure_log_includes_error_context(db_engine, test_settings: Settings, capsys) -> None:
    """Recovery failures must include error details + session context."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="log-failure@example.com", password_hash="x")
        session.add(user)
        session.commit()

        _insert_session_row(
            session,
            status=SessionStatus.STOPPING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=2,
            container_id="log-failure-1",
        )

        runtime = RecoveryRuntime(stop_error=True)
        poll_active_sessions_once(session, settings=test_settings, runtime=runtime)

        captured = capsys.readouterr()
        log_output = captured.out + captured.err

        assert "session.recovery.failure" in log_output or "stop_failed" in log_output, (
            f"Expected failure event in logs. Got: {log_output!r}"
        )


def test_correlation_id_present_in_recovery_logs(db_engine, test_settings: Settings, capsys) -> None:
    """Recovery logs must include correlation_id for tracing poll cycles."""
    with Session(db_engine) as session:
        pack = session.exec(select(Pack)).first()
        assert pack is not None
        user = User(id=uuid4(), email="log-corr@example.com", password_hash="x")
        session.add(user)
        session.commit()

        _insert_session_row(
            session,
            status=SessionStatus.STARTING,
            user_id=user.id,
            pack_id=pack.id,
            gpu_id=3,
            container_id="log-corr-1",
        )

        runtime = RecoveryRuntime(states={"log-corr-1": RuntimeContainerState.RUNNING})
        poll_active_sessions_once(session, settings=test_settings, runtime=runtime)

        captured = capsys.readouterr()
        log_output = captured.out + captured.err

        assert "correlation_id" in log_output, (
            f"Log output missing correlation_id. Got: {log_output!r}"
        )
