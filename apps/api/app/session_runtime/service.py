from __future__ import annotations

from app.session_runtime.ports import ContainerRuntimePort, SessionRuntime, WorkspaceRuntimePort
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


class SessionRuntimeService(SessionRuntime):
    """Runtime orchestration service.

    @filename app/session_runtime/adapters/docker_container.py
    @filename app/session_runtime/adapters/zfs_workspace.py
    """

    def __init__(
        self,
        *,
        workspace: WorkspaceRuntimePort,
        container: ContainerRuntimePort,
        container_name_prefix: str = "mf-session",
    ) -> None:
        self._workspace = workspace
        self._container = container
        self._container_name_prefix = container_name_prefix

    def _container_name(self, slug: str) -> str:
        return f"{self._container_name_prefix}-{slug}"

    def provision_workspace(self, request: WorkspaceProvisionRequest) -> WorkspaceProvisionResult:
        return self._workspace.provision_workspace(request)

    def start_session(self, request: SessionStartRequest) -> SessionStartResult:
        mountpoint = self._workspace.resolve_mountpoint(request.workspace_zfs)
        container_request = ContainerStartRequest(
            image_ref=request.pack_image_ref,
            container_name=self._container_name(request.slug),
            session_id=request.session_id,
            user_id=request.user_id,
            tier=request.tier,
            gpu_id=request.gpu_id,
            public_sessions_network=request.public_sessions_network,
            workspace_mount=mountpoint,
            start_timeout_seconds=request.start_timeout_seconds,
            resource_limits=request.resource_limits,
        )
        return self._container.start_container(container_request)

    def stop_session(self, request: SessionStopRequest) -> SessionStopResult:
        return self._container.stop_container(request)

    def snapshot_workspace(self, request: WorkspaceSnapshotRequest) -> WorkspaceSnapshotResult:
        return self._workspace.snapshot_workspace(request)

    def inspect_session(self, request: SessionInspectRequest) -> SessionInspectResult:
        inspect_request = ContainerInspectRequest(
            container_id=request.container_id,
            container_name=self._container_name(request.slug),
        )
        return self._container.inspect_container(inspect_request)

