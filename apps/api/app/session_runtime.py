from __future__ import annotations

import itertools
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import docker

from app.config import Settings
from app.models import Pack, SessionRecord


class SessionRuntimeError(RuntimeError):
    pass


class RuntimeContainerState(StrEnum):
    RUNNING = "running"
    EXITED = "exited"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ContainerInspection:
    state: RuntimeContainerState
    container_id: str | None = None


class SessionRuntime(Protocol):
    def ensure_workspace_dataset(
        self,
        workspace_zfs: str,
        *,
        uid: int,
        gid: int,
        quota_gb: int | None,
    ) -> None: ...

    def start_session_container(self, session_row: SessionRecord, pack: Pack) -> str: ...

    def stop_session_container(self, container_id: str | None, *, timeout_seconds: int) -> None: ...

    def snapshot_workspace(self, workspace_zfs: str, *, snapshot_name: str) -> None: ...

    def inspect_session_container(self, *, container_id: str | None, slug: str) -> ContainerInspection: ...


class MockSessionRuntime:
    _counter = itertools.count(start=1)

    def ensure_workspace_dataset(
        self,
        workspace_zfs: str,
        *,
        uid: int,
        gid: int,
        quota_gb: int | None,
    ) -> None:
        _ = (workspace_zfs, uid, gid, quota_gb)

    def start_session_container(self, session_row: SessionRecord, pack: Pack) -> str:
        _ = pack
        return f"mock-{session_row.slug}-{next(self._counter)}"

    def stop_session_container(self, container_id: str | None, *, timeout_seconds: int) -> None:
        _ = (container_id, timeout_seconds)

    def snapshot_workspace(self, workspace_zfs: str, *, snapshot_name: str) -> None:
        _ = (workspace_zfs, snapshot_name)

    def inspect_session_container(self, *, container_id: str | None, slug: str) -> ContainerInspection:
        _ = slug
        if not container_id:
            return ContainerInspection(state=RuntimeContainerState.MISSING)
        if container_id.startswith("exited-"):
            return ContainerInspection(state=RuntimeContainerState.EXITED, container_id=container_id)
        if container_id.startswith("missing-"):
            return ContainerInspection(state=RuntimeContainerState.MISSING)
        return ContainerInspection(state=RuntimeContainerState.RUNNING, container_id=container_id)


class DockerZfsSessionRuntime:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = docker.from_env()

    def _prefix(self) -> list[str]:
        if self._settings.session_runtime_use_sudo:
            return ["sudo", "-n"]
        return []

    def _run_cmd(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [*self._prefix(), *args]
        try:
            return subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            raise SessionRuntimeError(stderr) from exc

    def _dataset_exists(self, dataset: str) -> bool:
        cmd = [*self._prefix(), "zfs", "list", "-H", "-o", "name", dataset]
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _dataset_mountpoint(self, dataset: str) -> str:
        result = self._run_cmd(["zfs", "get", "-H", "-o", "value", "mountpoint", dataset])
        mountpoint = result.stdout.strip()
        if not mountpoint or mountpoint == "-":
            return f"/{dataset}"
        return mountpoint

    def ensure_workspace_dataset(
        self,
        workspace_zfs: str,
        *,
        uid: int,
        gid: int,
        quota_gb: int | None,
    ) -> None:
        if "/" not in workspace_zfs:
            raise SessionRuntimeError("Invalid workspace dataset path.")

        parent = workspace_zfs.rsplit("/", 1)[0]
        for dataset in (parent, workspace_zfs):
            if not self._dataset_exists(dataset):
                self._run_cmd(["zfs", "create", dataset])

        if quota_gb is not None and quota_gb > 0:
            self._run_cmd(["zfs", "set", f"quota={quota_gb}G", workspace_zfs])

        mountpoint = self._dataset_mountpoint(workspace_zfs)
        self._run_cmd(["chown", f"{uid}:{gid}", mountpoint])

    def _wait_until_running(self, container_id: str, timeout_seconds: int) -> None:
        timeout = max(timeout_seconds, 1)
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            container = self._client.containers.get(container_id)
            container.reload()
            status = container.status
            if status == "running":
                return
            if status in {"dead", "exited"}:
                raise SessionRuntimeError(f"Container exited before running (status={status}).")
            time.sleep(0.5)

        raise SessionRuntimeError("Container start timed out.")

    def start_session_container(self, session_row: SessionRecord, pack: Pack) -> str:
        workspace_mount = self._dataset_mountpoint(session_row.workspace_zfs)
        container_name = f"mf-session-{session_row.slug}"
        container_id: str | None = None

        env = {
            "MEDFORGE_SESSION_ID": str(session_row.id),
            "MEDFORGE_USER_ID": str(session_row.user_id),
            "MEDFORGE_TIER": session_row.tier.value,
            "MEDFORGE_GPU_ID": str(session_row.gpu_id),
            "NVIDIA_VISIBLE_DEVICES": str(session_row.gpu_id),
            "CUDA_VISIBLE_DEVICES": "0",
        }

        device_request = docker.types.DeviceRequest(
            device_ids=[str(session_row.gpu_id)],
            capabilities=[["gpu"]],
        )

        resource_kwargs: dict[str, object] = {
            "cpu_shares": self._settings.session_cpu_shares,
        }
        if self._settings.session_cpu_limit is not None:
            resource_kwargs["nano_cpus"] = self._settings.session_cpu_limit * 10**9
        if self._settings.session_mem_limit is not None:
            resource_kwargs["mem_limit"] = self._settings.session_mem_limit
            resource_kwargs["memswap_limit"] = self._settings.session_mem_limit
        if self._settings.session_mem_reservation is not None:
            resource_kwargs["mem_reservation"] = self._settings.session_mem_reservation
        if self._settings.session_shm_size is not None:
            resource_kwargs["shm_size"] = self._settings.session_shm_size
        if self._settings.session_pids_limit is not None:
            resource_kwargs["pids_limit"] = self._settings.session_pids_limit

        try:
            container = self._client.containers.run(
                pack.image_ref,
                name=container_name,
                detach=True,
                network=self._settings.public_sessions_network,
                user="1000:1000",
                cap_drop=["ALL"],
                privileged=False,
                security_opt=["no-new-privileges:true"],
                environment=env,
                volumes={workspace_mount: {"bind": "/workspace", "mode": "rw"}},
                device_requests=[device_request],
                **resource_kwargs,
            )
            container_id = str(container.id)
            self._wait_until_running(container_id, self._settings.session_container_start_timeout_seconds)
            return container_id
        except Exception as exc:
            if container_id:
                try:
                    failed = self._client.containers.get(container_id)
                    failed.remove(force=True)
                except Exception:
                    pass
            raise SessionRuntimeError(f"Unable to start container: {exc}") from exc

    def stop_session_container(self, container_id: str | None, *, timeout_seconds: int) -> None:
        if not container_id:
            return
        try:
            container = self._client.containers.get(container_id)
        except docker.errors.NotFound:
            return
        except docker.errors.APIError as exc:
            raise SessionRuntimeError(f"Unable to find container for stop: {exc.explanation}") from exc

        stop_timeout = max(timeout_seconds, 1)
        try:
            container.reload()
        except docker.errors.NotFound:
            return
        except docker.errors.APIError as exc:
            raise SessionRuntimeError(f"Unable to inspect container before stop: {exc.explanation}") from exc

        if container.status not in {"dead", "exited"}:
            try:
                container.stop(timeout=stop_timeout)
            except docker.errors.NotFound:
                return
            except docker.errors.APIError:
                try:
                    container.kill()
                except docker.errors.NotFound:
                    return
                except docker.errors.APIError:
                    pass

        try:
            container.remove(force=True)
        except docker.errors.NotFound:
            return
        except docker.errors.APIError as exc:
            raise SessionRuntimeError(f"Unable to remove container: {exc.explanation}") from exc

    def snapshot_workspace(self, workspace_zfs: str, *, snapshot_name: str) -> None:
        self._run_cmd(["zfs", "snapshot", f"{workspace_zfs}@{snapshot_name}"])

    def inspect_session_container(self, *, container_id: str | None, slug: str) -> ContainerInspection:
        container = None
        if container_id:
            try:
                container = self._client.containers.get(container_id)
            except docker.errors.NotFound:
                container = None
            except docker.errors.APIError as exc:
                raise SessionRuntimeError(f"Unable to inspect container: {exc.explanation}") from exc

        if container is None:
            name = f"mf-session-{slug}"
            try:
                container = self._client.containers.get(name)
            except docker.errors.NotFound:
                return ContainerInspection(state=RuntimeContainerState.MISSING)
            except docker.errors.APIError as exc:
                raise SessionRuntimeError(f"Unable to inspect container: {exc.explanation}") from exc

        try:
            container.reload()
        except docker.errors.NotFound:
            return ContainerInspection(state=RuntimeContainerState.MISSING)
        except docker.errors.APIError as exc:
            raise SessionRuntimeError(f"Unable to inspect container: {exc.explanation}") from exc

        status = container.status
        if status == "running":
            return ContainerInspection(state=RuntimeContainerState.RUNNING, container_id=str(container.id))
        if status in {"dead", "exited"}:
            return ContainerInspection(state=RuntimeContainerState.EXITED, container_id=str(container.id))
        return ContainerInspection(state=RuntimeContainerState.UNKNOWN, container_id=str(container.id))


def get_session_runtime(settings: Settings) -> SessionRuntime:
    mode = settings.session_runtime_mode.strip().lower()
    if mode == "mock":
        return MockSessionRuntime()
    return DockerZfsSessionRuntime(settings)
