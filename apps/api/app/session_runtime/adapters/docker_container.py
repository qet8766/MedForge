from __future__ import annotations

import logging

import docker

from app.session_runtime.adapters.docker_inspect import inspect_container
from app.session_runtime.adapters.docker_start import run_container, wait_until_running
from app.session_runtime.adapters.docker_stop import stop_container
from app.session_runtime.types import (
    ContainerInspectRequest,
    ContainerStartRequest,
    RuntimeErrorCode,
    SessionInspectResult,
    SessionRuntimeError,
    SessionStartResult,
    SessionStopRequest,
)

log = logging.getLogger(__name__)


class DockerContainerAdapter:
    """Docker runtime adapter.

    @filename app/session_runtime/adapters/docker_start.py
    @filename app/session_runtime/adapters/docker_stop.py
    @filename app/session_runtime/adapters/docker_inspect.py
    """

    def __init__(self) -> None:
        self._client = docker.from_env()

    def start_container(self, request: ContainerStartRequest) -> SessionStartResult:
        container_id: str | None = None
        try:
            container_id = run_container(self._client, request)
            wait_until_running(self._client, container_id, timeout_seconds=request.start_timeout_seconds)
            return SessionStartResult(container_id=container_id)
        except SessionRuntimeError:
            if container_id is not None:
                self._cleanup_failed_container(container_id)
            raise
        except Exception as exc:
            if container_id is not None:
                self._cleanup_failed_container(container_id)
            raise SessionRuntimeError(
                code=RuntimeErrorCode.CONTAINER_START_FAILED,
                operation="container.start",
                message=f"Unable to start container: {exc}",
                cause=exc,
            ) from exc

    def _cleanup_failed_container(self, container_id: str) -> None:
        try:
            failed = self._client.containers.get(container_id)
            failed.remove(force=True)
        except Exception:
            log.warning("cleanup_failed_container: unable to remove container_id=%s", container_id, exc_info=True)

    def stop_container(self, request: SessionStopRequest) -> None:
        return stop_container(self._client, request)

    def inspect_container(self, request: ContainerInspectRequest) -> SessionInspectResult:
        return inspect_container(self._client, request)
