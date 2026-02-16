from __future__ import annotations

import subprocess

from app.session_runtime.types import (
    RuntimeErrorCode,
    SessionRuntimeError,
    WorkspaceProvisionRequest,
    WorkspaceProvisionResult,
    WorkspaceSnapshotRequest,
    WorkspaceSnapshotResult,
)


class ZfsWorkspaceAdapter:
    def __init__(self, *, use_sudo: bool) -> None:
        self._use_sudo = use_sudo

    def _prefix(self) -> list[str]:
        if self._use_sudo:
            return ["sudo", "-n"]
        return []

    def _run_cmd(self, args: list[str], *, error_code: RuntimeErrorCode) -> subprocess.CompletedProcess[str]:
        cmd = [*self._prefix(), *args]
        operation = " ".join(args)
        try:
            return subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            raise SessionRuntimeError(
                code=error_code,
                operation=operation,
                message=stderr,
                cause=exc,
            ) from exc

    def _dataset_exists(self, dataset: str) -> bool:
        cmd = [*self._prefix(), "zfs", "list", "-H", "-o", "name", dataset]
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        except OSError as exc:
            raise SessionRuntimeError(
                code=RuntimeErrorCode.WORKSPACE_COMMAND_FAILED,
                operation="zfs list",
                message=str(exc),
                cause=exc,
            ) from exc
        return result.returncode == 0

    def resolve_mountpoint(self, workspace_zfs: str) -> str:
        result = self._run_cmd(
            ["zfs", "get", "-H", "-o", "value", "mountpoint", workspace_zfs],
            error_code=RuntimeErrorCode.WORKSPACE_COMMAND_FAILED,
        )
        mountpoint = result.stdout.strip()
        if not mountpoint or mountpoint == "-":
            return f"/{workspace_zfs}"
        return mountpoint

    def provision_workspace(self, request: WorkspaceProvisionRequest) -> WorkspaceProvisionResult:
        workspace_zfs = request.workspace_zfs
        if "/" not in workspace_zfs:
            raise SessionRuntimeError(
                code=RuntimeErrorCode.WORKSPACE_INVALID_PATH,
                operation="workspace.validate_path",
                message="Invalid workspace dataset path.",
            )

        parent = workspace_zfs.rsplit("/", 1)[0]
        for dataset in (parent, workspace_zfs):
            if not self._dataset_exists(dataset):
                self._run_cmd(
                    ["zfs", "create", dataset],
                    error_code=RuntimeErrorCode.WORKSPACE_COMMAND_FAILED,
                )

        if request.quota_gb is not None and request.quota_gb > 0:
            self._run_cmd(
                ["zfs", "set", f"quota={request.quota_gb}G", workspace_zfs],
                error_code=RuntimeErrorCode.WORKSPACE_COMMAND_FAILED,
            )

        mountpoint = self.resolve_mountpoint(workspace_zfs)
        self._run_cmd(
            ["chown", f"{request.uid}:{request.gid}", mountpoint],
            error_code=RuntimeErrorCode.WORKSPACE_COMMAND_FAILED,
        )
        return WorkspaceProvisionResult(workspace_zfs=workspace_zfs, mountpoint=mountpoint)

    def snapshot_workspace(self, request: WorkspaceSnapshotRequest) -> WorkspaceSnapshotResult:
        dataset_snapshot = f"{request.workspace_zfs}@{request.snapshot_name}"
        self._run_cmd(
            ["zfs", "snapshot", dataset_snapshot],
            error_code=RuntimeErrorCode.SNAPSHOT_FAILED,
        )
        return WorkspaceSnapshotResult(
            workspace_zfs=request.workspace_zfs,
            snapshot_name=request.snapshot_name,
        )

