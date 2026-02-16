from __future__ import annotations

import itertools

from app.session_runtime.service import SessionRuntimeService
from app.session_runtime.types import (
    ContainerInspectRequest,
    ContainerStartRequest,
    RuntimeContainerState,
    SessionInspectResult,
    SessionStartResult,
    SessionStopRequest,
    SessionStopResult,
    WorkspaceProvisionRequest,
    WorkspaceProvisionResult,
    WorkspaceSnapshotRequest,
    WorkspaceSnapshotResult,
)


class MockWorkspaceAdapter:
    def resolve_mountpoint(self, workspace_zfs: str) -> str:
        return f"/{workspace_zfs.strip('/')}"

    def provision_workspace(self, request: WorkspaceProvisionRequest) -> WorkspaceProvisionResult:
        mountpoint = self.resolve_mountpoint(request.workspace_zfs)
        return WorkspaceProvisionResult(workspace_zfs=request.workspace_zfs, mountpoint=mountpoint)

    def snapshot_workspace(self, request: WorkspaceSnapshotRequest) -> WorkspaceSnapshotResult:
        return WorkspaceSnapshotResult(
            workspace_zfs=request.workspace_zfs,
            snapshot_name=request.snapshot_name,
        )


class MockContainerAdapter:
    _counter = itertools.count(start=1)

    def start_container(self, request: ContainerStartRequest) -> SessionStartResult:
        slug = request.container_name.split("-")[-1]
        return SessionStartResult(container_id=f"mock-{slug}-{next(self._counter)}")

    def stop_container(self, request: SessionStopRequest) -> SessionStopResult:
        return SessionStopResult(removed=bool(request.container_id))

    def inspect_container(self, request: ContainerInspectRequest) -> SessionInspectResult:
        container_id = request.container_id
        if not container_id:
            return SessionInspectResult(state=RuntimeContainerState.MISSING)
        if container_id.startswith("exited-"):
            return SessionInspectResult(state=RuntimeContainerState.EXITED, container_id=container_id)
        if container_id.startswith("missing-"):
            return SessionInspectResult(state=RuntimeContainerState.MISSING)
        if container_id.startswith("unknown-"):
            return SessionInspectResult(state=RuntimeContainerState.UNKNOWN, container_id=container_id)
        return SessionInspectResult(state=RuntimeContainerState.RUNNING, container_id=container_id)


class MockSessionRuntime(SessionRuntimeService):
    def __init__(self) -> None:
        super().__init__(
            workspace=MockWorkspaceAdapter(),
            container=MockContainerAdapter(),
        )
