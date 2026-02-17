from __future__ import annotations

from uuid import uuid4

from app.config import Settings
from app.session_runtime import (
    MockSessionRuntime,
    RuntimeContainerState,
    SessionInspectRequest,
    SessionInspectResult,
    SessionResourceLimits,
    SessionRuntimeService,
    SessionStartRequest,
    SessionStartResult,
    SessionStopRequest,
    WorkspaceProvisionRequest,
    WorkspaceProvisionResult,
    WorkspaceSnapshotRequest,
    WorkspaceSnapshotResult,
    get_session_runtime,
)


class RecordingWorkspacePort:
    def __init__(self, mountpoint: str) -> None:
        self.mountpoint = mountpoint
        self.resolve_calls: list[str] = []

    def resolve_mountpoint(self, workspace_zfs: str) -> str:
        self.resolve_calls.append(workspace_zfs)
        return self.mountpoint

    def provision_workspace(self, request: WorkspaceProvisionRequest) -> WorkspaceProvisionResult:
        return WorkspaceProvisionResult(workspace_zfs=request.workspace_zfs, mountpoint=self.mountpoint)

    def snapshot_workspace(self, request: WorkspaceSnapshotRequest) -> WorkspaceSnapshotResult:
        return WorkspaceSnapshotResult(
            workspace_zfs=request.workspace_zfs,
            snapshot_name=request.snapshot_name,
        )


class RecordingContainerPort:
    def __init__(self) -> None:
        self.last_start = None
        self.last_inspect = None

    def start_container(self, request: object) -> SessionStartResult:
        self.last_start = request
        return SessionStartResult(container_id="cid-1")

    def stop_container(self, request: SessionStopRequest) -> None:
        _ = request
        return

    def inspect_container(self, request: object) -> SessionInspectResult:
        self.last_inspect = request
        return SessionInspectResult(state=RuntimeContainerState.MISSING)


def test_service_start_builds_container_name_and_uses_workspace_mountpoint() -> None:
    workspace = RecordingWorkspacePort(mountpoint="/mnt/workspace")
    container = RecordingContainerPort()
    runtime = SessionRuntimeService(workspace=workspace, container=container, container_name_prefix="mf-session")

    result = runtime.start_session(
        SessionStartRequest(
            session_id=uuid4(),
            user_id=uuid4(),
            exposure="EXTERNAL",
            slug="abc123de",
            gpu_id=0,
            workspace_zfs="tank/medforge/workspaces/u/s",
            pack_image_ref="image@sha256:123",
            sessions_network="medforge-external-sessions",
            start_timeout_seconds=5,
            resource_limits=SessionResourceLimits(cpu_shares=1024),
        )
    )

    assert result.container_id == "cid-1"
    assert workspace.resolve_calls == ["tank/medforge/workspaces/u/s"]
    assert container.last_start is not None
    assert container.last_start.container_name == "mf-session-abc123de"
    assert container.last_start.workspace_mount == "/mnt/workspace"


def test_service_inspect_passes_resolved_container_name() -> None:
    workspace = RecordingWorkspacePort(mountpoint="/mnt/workspace")
    container = RecordingContainerPort()
    runtime = SessionRuntimeService(workspace=workspace, container=container)

    result = runtime.inspect_session(SessionInspectRequest(container_id=None, slug="abc123de"))

    assert result.state == RuntimeContainerState.MISSING
    assert container.last_inspect is not None
    assert container.last_inspect.container_name == "mf-session-abc123de"


def test_mock_runtime_inspection_defaults() -> None:
    runtime = MockSessionRuntime()

    running = runtime.inspect_session(SessionInspectRequest(container_id="running-1", slug="slug1234"))
    exited = runtime.inspect_session(SessionInspectRequest(container_id="exited-1", slug="slug1234"))
    missing = runtime.inspect_session(SessionInspectRequest(container_id=None, slug="slug1234"))

    assert running.state == RuntimeContainerState.RUNNING
    assert exited.state == RuntimeContainerState.EXITED
    assert missing.state == RuntimeContainerState.MISSING


def test_factory_returns_mock_runtime_in_mock_mode() -> None:
    settings = Settings(session_runtime_mode="mock")
    runtime = get_session_runtime(settings)
    assert isinstance(runtime, MockSessionRuntime)
