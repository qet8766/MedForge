from __future__ import annotations

import importlib
from dataclasses import replace
from types import ModuleType

import pytest
from fastapi import Response

from app.config import Settings


class DummySessionContext:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type, exc, tb) -> bool:
        _ = (exc_type, exc, tb)
        return False


class RecordingStopEvent:
    def __init__(self, *, stop_after_waits: int) -> None:
        self._stop_after_waits = stop_after_waits
        self._is_set = False
        self.wait_calls: list[int] = []
        self.set_calls = 0

    def is_set(self) -> bool:
        return self._is_set

    def set(self) -> None:
        self.set_calls += 1
        self._is_set = True

    def wait(self, timeout: int) -> bool:
        self.wait_calls.append(timeout)
        if len(self.wait_calls) >= self._stop_after_waits:
            self._is_set = True
        return self._is_set


class DummyThread:
    def __init__(self) -> None:
        self.join_timeout: int | None = None

    def is_alive(self) -> bool:
        return True

    def join(self, timeout: int | None = None) -> None:
        self.join_timeout = timeout


class AliveThread:
    def is_alive(self) -> bool:
        return True


@pytest.fixture()
def main_module() -> ModuleType:
    import app.main as app_main

    return importlib.reload(app_main)


def _run_recovery_loop(
    module: ModuleType,
    monkeypatch,
    *,
    outcomes: list[int | Exception],
    stop_after_waits: int,
    poll_interval_seconds: int,
    poll_backoff_max_seconds: int,
) -> RecordingStopEvent:
    module.settings = replace(
        module.settings,
        session_recovery_enabled=True,
        session_poll_interval_seconds=poll_interval_seconds,
        session_poll_backoff_max_seconds=poll_backoff_max_seconds,
    )
    stop_event = RecordingStopEvent(stop_after_waits=stop_after_waits)
    monkeypatch.setattr(module, "_recovery_stop_event", stop_event)
    monkeypatch.setattr(module, "Session", lambda _engine: DummySessionContext())

    remaining = outcomes.copy()

    def poll_stub(_session, *, settings: Settings) -> int:
        _ = settings
        if not remaining:
            return 0
        result = remaining.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(module, "poll_active_sessions_once", poll_stub)
    module._session_recovery_loop()
    return stop_event


def _health_response(module: ModuleType) -> tuple[int, dict[str, str]]:
    response = Response()
    payload = module.healthz(response)
    return response.status_code, payload


@pytest.mark.asyncio
async def test_lifespan_runs_reconcile_and_recovery_thread_lifecycle_when_enabled(main_module, monkeypatch) -> None:
    main_module.settings = replace(main_module.settings, session_recovery_enabled=True)
    calls: list[str] = []

    monkeypatch.setattr(main_module, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(main_module, "Session", lambda _engine: DummySessionContext())
    monkeypatch.setattr(main_module, "seed_defaults", lambda _session: calls.append("seed_defaults"))
    monkeypatch.setattr(main_module, "reconcile_on_startup", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(main_module, "_start_session_recovery_thread", lambda: calls.append("start_recovery_thread"))
    monkeypatch.setattr(main_module, "_stop_session_recovery_thread", lambda: calls.append("stop_recovery_thread"))

    async with main_module.lifespan(main_module.app):
        pass

    assert "init_db" in calls
    assert "seed_defaults" in calls
    assert "start_recovery_thread" in calls
    assert "stop_recovery_thread" in calls


@pytest.mark.asyncio
async def test_lifespan_skips_reconcile_and_start_when_recovery_disabled(main_module, monkeypatch) -> None:
    main_module.settings = replace(main_module.settings, session_recovery_enabled=False)
    calls: list[str] = []

    monkeypatch.setattr(main_module, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(main_module, "Session", lambda _engine: DummySessionContext())
    monkeypatch.setattr(main_module, "seed_defaults", lambda _session: calls.append("seed_defaults"))
    monkeypatch.setattr(main_module, "reconcile_on_startup", lambda *_args, **_kwargs: calls.append("reconcile"))
    monkeypatch.setattr(main_module, "_start_session_recovery_thread", lambda: calls.append("start_recovery_thread"))
    monkeypatch.setattr(main_module, "_stop_session_recovery_thread", lambda: calls.append("stop_recovery_thread"))

    async with main_module.lifespan(main_module.app):
        pass

    assert "init_db" in calls
    assert "seed_defaults" in calls
    assert "reconcile" not in calls
    assert "start_recovery_thread" not in calls
    assert calls.count("stop_recovery_thread") == 1


def test_stop_session_recovery_thread_sets_event_joins_and_clears_thread(main_module, monkeypatch) -> None:
    stop_event = RecordingStopEvent(stop_after_waits=99)
    thread = DummyThread()
    monkeypatch.setattr(main_module, "_recovery_stop_event", stop_event)
    monkeypatch.setattr(main_module, "_recovery_thread", thread)

    main_module._stop_session_recovery_thread()

    assert stop_event.set_calls == 1
    assert thread.join_timeout == 5
    assert main_module._recovery_thread is None


def test_session_poll_backoff_caps_wait_interval(main_module, monkeypatch) -> None:
    stop_event = _run_recovery_loop(
        main_module,
        monkeypatch,
        outcomes=[RuntimeError("poll failed")] * 4,
        stop_after_waits=4,
        poll_interval_seconds=1,
        poll_backoff_max_seconds=4,
    )

    assert stop_event.wait_calls == [2, 4, 4, 4]


def test_healthz_returns_503_when_recovery_enabled_without_live_thread(main_module, monkeypatch) -> None:
    main_module.settings = replace(main_module.settings, session_recovery_enabled=True)
    monkeypatch.setattr(main_module, "_recovery_thread", None)

    status_code, payload = _health_response(main_module)
    assert status_code == 503
    assert payload["status"] == "degraded"


def test_healthz_returns_200_with_live_recovery_thread(main_module, monkeypatch) -> None:
    main_module.settings = replace(main_module.settings, session_recovery_enabled=True)
    monkeypatch.setattr(main_module, "_recovery_thread", AliveThread())

    status_code, payload = _health_response(main_module)
    assert status_code == 200
    assert payload["status"] == "ok"


def test_settings_reads_session_poll_backoff_max_seconds_env(monkeypatch) -> None:
    monkeypatch.setenv("SESSION_POLL_BACKOFF_MAX_SECONDS", "17")
    assert Settings().session_poll_backoff_max_seconds == 17
