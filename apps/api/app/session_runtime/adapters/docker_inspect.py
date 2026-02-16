from __future__ import annotations

import docker

from app.session_runtime.types import (
    ContainerInspectRequest,
    RuntimeContainerState,
    RuntimeErrorCode,
    SessionInspectResult,
    SessionRuntimeError,
)


def _api_message(exc: docker.errors.APIError) -> str:
    return exc.explanation if exc.explanation else str(exc)


def inspect_container(client: docker.DockerClient, request: ContainerInspectRequest) -> SessionInspectResult:
    container = None
    if request.container_id:
        try:
            container = client.containers.get(request.container_id)
        except docker.errors.NotFound:
            container = None
        except docker.errors.APIError as exc:
            raise SessionRuntimeError(
                code=RuntimeErrorCode.CONTAINER_INSPECT_FAILED,
                operation="container.inspect.by_id",
                message=_api_message(exc),
                cause=exc,
            ) from exc

    if container is None:
        try:
            container = client.containers.get(request.container_name)
        except docker.errors.NotFound:
            return SessionInspectResult(state=RuntimeContainerState.MISSING)
        except docker.errors.APIError as exc:
            raise SessionRuntimeError(
                code=RuntimeErrorCode.CONTAINER_INSPECT_FAILED,
                operation="container.inspect.by_name",
                message=_api_message(exc),
                cause=exc,
            ) from exc

    try:
        container.reload()
    except docker.errors.NotFound:
        return SessionInspectResult(state=RuntimeContainerState.MISSING)
    except docker.errors.APIError as exc:
        raise SessionRuntimeError(
            code=RuntimeErrorCode.CONTAINER_INSPECT_FAILED,
            operation="container.inspect.reload",
            message=_api_message(exc),
            cause=exc,
        ) from exc

    status = container.status
    container_id = str(container.id)
    if status == "running":
        return SessionInspectResult(state=RuntimeContainerState.RUNNING, container_id=container_id)
    if status in {"dead", "exited"}:
        return SessionInspectResult(state=RuntimeContainerState.EXITED, container_id=container_id)
    return SessionInspectResult(state=RuntimeContainerState.UNKNOWN, container_id=container_id)

