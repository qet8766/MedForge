from __future__ import annotations

from typing import Protocol

from app.session_runtime.types import (
    ContainerInspectRequest,
    ContainerStartRequest,
    SessionInspectRequest,
    SessionInspectResult,
    SessionStartRequest,
    SessionStartResult,
    SessionStopRequest,
    SessionStopResult,
    WorkspaceProvisionRequest,
    WorkspaceProvisionResult,
    WorkspaceSnapshotRequest,
    WorkspaceSnapshotResult,
)


class WorkspaceRuntimePort(Protocol):
    def resolve_mountpoint(self, workspace_zfs: str) -> str: ...

    def provision_workspace(self, request: WorkspaceProvisionRequest) -> WorkspaceProvisionResult: ...

    def snapshot_workspace(self, request: WorkspaceSnapshotRequest) -> WorkspaceSnapshotResult: ...


class ContainerRuntimePort(Protocol):
    def start_container(self, request: ContainerStartRequest) -> SessionStartResult: ...

    def stop_container(self, request: SessionStopRequest) -> SessionStopResult: ...

    def inspect_container(self, request: ContainerInspectRequest) -> SessionInspectResult: ...


class SessionRuntime(Protocol):
    def provision_workspace(self, request: WorkspaceProvisionRequest) -> WorkspaceProvisionResult: ...

    def start_session(self, request: SessionStartRequest) -> SessionStartResult: ...

    def stop_session(self, request: SessionStopRequest) -> SessionStopResult: ...

    def snapshot_workspace(self, request: WorkspaceSnapshotRequest) -> WorkspaceSnapshotResult: ...

    def inspect_session(self, request: SessionInspectRequest) -> SessionInspectResult: ...

