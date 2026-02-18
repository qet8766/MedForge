from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class RuntimeContainerState(StrEnum):
    RUNNING = "running"
    EXITED = "exited"
    MISSING = "missing"
    UNKNOWN = "unknown"


class RuntimeErrorCode(StrEnum):
    WORKSPACE_INVALID_PATH = "workspace_invalid_path"
    WORKSPACE_COMMAND_FAILED = "workspace_command_failed"
    CONTAINER_START_FAILED = "container_start_failed"
    CONTAINER_START_TIMEOUT = "container_start_timeout"
    CONTAINER_INSPECT_FAILED = "container_inspect_failed"
    CONTAINER_STOP_FAILED = "container_stop_failed"
    CONTAINER_REMOVE_FAILED = "container_remove_failed"
    SNAPSHOT_FAILED = "snapshot_failed"


class SessionRuntimeError(RuntimeError):
    def __init__(
        self,
        *,
        code: RuntimeErrorCode,
        operation: str,
        message: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.operation = operation
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        return f"{self.message} [code={self.code.value}, operation={self.operation}]"


@dataclass(frozen=True)
class SessionResourceLimits:
    cpu_shares: int
    cpu_limit: int | None = None
    mem_limit: str | None = None
    mem_reservation: str | None = None
    shm_size: str | None = None
    pids_limit: int | None = None


@dataclass(frozen=True)
class WorkspaceProvisionRequest:
    workspace_zfs: str
    uid: int
    gid: int
    quota_gb: int | None


@dataclass(frozen=True)
class WorkspaceProvisionResult:
    workspace_zfs: str
    mountpoint: str


@dataclass(frozen=True)
class WorkspaceSnapshotRequest:
    workspace_zfs: str
    snapshot_name: str


@dataclass(frozen=True)
class WorkspaceSnapshotResult:
    workspace_zfs: str
    snapshot_name: str


@dataclass(frozen=True)
class SessionStartRequest:
    session_id: UUID
    user_id: UUID
    exposure: str
    slug: str
    gpu_id: int
    workspace_zfs: str
    pack_image_ref: str
    sessions_network: str
    start_timeout_seconds: int
    resource_limits: SessionResourceLimits
    ssh_port: int = 0
    ssh_public_key: str | None = None


@dataclass(frozen=True)
class SessionStartResult:
    container_id: str


@dataclass(frozen=True)
class SessionStopRequest:
    container_id: str | None
    timeout_seconds: int


@dataclass(frozen=True)
class SessionInspectRequest:
    container_id: str | None
    slug: str


@dataclass(frozen=True)
class SessionInspectResult:
    state: RuntimeContainerState
    container_id: str | None = None


@dataclass(frozen=True)
class ContainerStartRequest:
    image_ref: str
    container_name: str
    session_id: UUID
    user_id: UUID
    exposure: str
    gpu_id: int
    sessions_network: str
    workspace_mount: str
    start_timeout_seconds: int
    resource_limits: SessionResourceLimits
    ssh_port: int = 0
    ssh_public_key: str | None = None


@dataclass(frozen=True)
class ContainerInspectRequest:
    container_id: str | None
    container_name: str
