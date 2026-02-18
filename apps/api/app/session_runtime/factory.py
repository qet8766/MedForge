from __future__ import annotations

from app.config import Settings
from app.session_runtime.adapters.docker_container import DockerContainerAdapter
from app.session_runtime.adapters.mock import MockSessionRuntime
from app.session_runtime.adapters.zfs_workspace import ZfsWorkspaceAdapter
from app.session_runtime.ports import SessionRuntime
from app.session_runtime.service import SessionRuntimeService


def get_session_runtime(settings: Settings) -> SessionRuntime:
    mode = settings.session_runtime_mode.strip().lower()
    if mode == "mock":
        return MockSessionRuntime()

    workspace = ZfsWorkspaceAdapter(use_sudo=settings.session_runtime_use_sudo)
    container = DockerContainerAdapter()
    return SessionRuntimeService(workspace=workspace, container=container)
