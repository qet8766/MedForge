from __future__ import annotations

import docker

from app.session_runtime.types import (
    RuntimeErrorCode,
    SessionRuntimeError,
    SessionStopRequest,
    SessionStopResult,
)


def _api_message(exc: docker.errors.APIError) -> str:
    return exc.explanation if exc.explanation else str(exc)


def stop_container(client: docker.DockerClient, request: SessionStopRequest) -> SessionStopResult:
    if not request.container_id:
        return SessionStopResult(removed=False)
    try:
        container = client.containers.get(request.container_id)
    except docker.errors.NotFound:
        return SessionStopResult(removed=False)
    except docker.errors.APIError as exc:
        raise SessionRuntimeError(
            code=RuntimeErrorCode.CONTAINER_STOP_FAILED,
            operation="container.stop.lookup",
            message=_api_message(exc),
            cause=exc,
        ) from exc

    stop_timeout = max(request.timeout_seconds, 1)
    try:
        container.reload()
    except docker.errors.NotFound:
        return SessionStopResult(removed=False)
    except docker.errors.APIError as exc:
        raise SessionRuntimeError(
            code=RuntimeErrorCode.CONTAINER_INSPECT_FAILED,
            operation="container.stop.inspect",
            message=_api_message(exc),
            cause=exc,
        ) from exc

    if container.status not in {"dead", "exited"}:
        try:
            container.stop(timeout=stop_timeout)
        except docker.errors.NotFound:
            return SessionStopResult(removed=False)
        except docker.errors.APIError:
            try:
                container.kill()
            except docker.errors.NotFound:
                return SessionStopResult(removed=False)
            except docker.errors.APIError as exc:
                raise SessionRuntimeError(
                    code=RuntimeErrorCode.CONTAINER_STOP_FAILED,
                    operation="container.stop.kill",
                    message=_api_message(exc),
                    cause=exc,
                ) from exc

    try:
        container.remove(force=True)
    except docker.errors.NotFound:
        return SessionStopResult(removed=False)
    except docker.errors.APIError as exc:
        raise SessionRuntimeError(
            code=RuntimeErrorCode.CONTAINER_REMOVE_FAILED,
            operation="container.stop.remove",
            message=_api_message(exc),
            cause=exc,
        ) from exc

    return SessionStopResult(removed=True)

