from __future__ import annotations

import time

import docker

from app.session_runtime.types import (
    ContainerStartRequest,
    RuntimeErrorCode,
    SessionRuntimeError,
)


def _api_message(exc: docker.errors.APIError) -> str:
    return exc.explanation if exc.explanation else str(exc)


def wait_until_running(client: docker.DockerClient, container_id: str, *, timeout_seconds: int) -> None:
    timeout = max(timeout_seconds, 1)
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            container = client.containers.get(container_id)
        except docker.errors.NotFound as exc:
            raise SessionRuntimeError(
                code=RuntimeErrorCode.CONTAINER_START_FAILED,
                operation="container.wait_running",
                message="Container disappeared before reaching running state.",
                cause=exc,
            ) from exc
        except docker.errors.APIError as exc:
            raise SessionRuntimeError(
                code=RuntimeErrorCode.CONTAINER_INSPECT_FAILED,
                operation="container.wait_running",
                message=_api_message(exc),
                cause=exc,
            ) from exc

        container.reload()
        status = container.status
        if status == "running":
            return
        if status in {"dead", "exited"}:
            raise SessionRuntimeError(
                code=RuntimeErrorCode.CONTAINER_START_FAILED,
                operation="container.wait_running",
                message=f"Container exited before running (status={status}).",
            )
        time.sleep(0.5)

    raise SessionRuntimeError(
        code=RuntimeErrorCode.CONTAINER_START_TIMEOUT,
        operation="container.wait_running",
        message="Container start timed out.",
    )


def _resource_kwargs(request: ContainerStartRequest) -> dict[str, object]:
    kwargs: dict[str, object] = {"cpu_shares": request.resource_limits.cpu_shares}
    if request.resource_limits.cpu_limit is not None:
        kwargs["nano_cpus"] = request.resource_limits.cpu_limit * 10**9
    if request.resource_limits.mem_limit is not None:
        kwargs["mem_limit"] = request.resource_limits.mem_limit
        kwargs["memswap_limit"] = request.resource_limits.mem_limit
    if request.resource_limits.mem_reservation is not None:
        kwargs["mem_reservation"] = request.resource_limits.mem_reservation
    if request.resource_limits.shm_size is not None:
        kwargs["shm_size"] = request.resource_limits.shm_size
    if request.resource_limits.pids_limit is not None:
        kwargs["pids_limit"] = request.resource_limits.pids_limit
    return kwargs


def run_container(client: docker.DockerClient, request: ContainerStartRequest) -> str:
    env = {
        "MEDFORGE_SESSION_ID": str(request.session_id),
        "MEDFORGE_USER_ID": str(request.user_id),
        "MEDFORGE_EXPOSURE": request.exposure,
        "MEDFORGE_GPU_ID": str(request.gpu_id),
        "NVIDIA_VISIBLE_DEVICES": str(request.gpu_id),
        "CUDA_VISIBLE_DEVICES": "0",
    }
    device_request = docker.types.DeviceRequest(
        device_ids=[str(request.gpu_id)],
        capabilities=[["gpu"]],
    )

    container = client.containers.run(
        request.image_ref,
        name=request.container_name,
        detach=True,
        network=request.sessions_network,
        user="1000:1000",
        cap_drop=["ALL"],
        privileged=False,
        security_opt=["no-new-privileges:true"],
        environment=env,
        volumes={request.workspace_mount: {"bind": "/workspace", "mode": "rw"}},
        device_requests=[device_request],
        **_resource_kwargs(request),
    )
    return str(container.id)
