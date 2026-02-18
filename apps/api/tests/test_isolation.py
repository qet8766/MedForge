"""MF-101: Session isolation tests.

Validates that session containers cannot communicate with each other
at the network level (east-west isolation).

Tests marked with @pytest.mark.docker require real Docker runtime.
These are skipped in CI and run manually on the host.
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.docker


@pytest.fixture()
def _require_docker() -> None:
    """Skip if docker is not available."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("Docker daemon not available")
    except FileNotFoundError:
        pytest.skip("docker CLI not found")
    except subprocess.TimeoutExpired:
        pytest.skip("Docker daemon not responding")


def _list_session_containers() -> list[str]:
    """List running mf-session-* container names."""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=mf-session-"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return [name.strip() for name in result.stdout.splitlines() if name.strip()]


@pytest.mark.usefixtures("_require_docker")
def test_session_container_cannot_reach_other_session_http() -> None:
    """From session A, attempt HTTP to session B's :8080 → must fail."""
    containers = _list_session_containers()
    if len(containers) < 2:
        pytest.skip(f"Need >=2 running session containers, found {len(containers)}")

    source = containers[0]
    target = containers[1]

    result = subprocess.run(
        [
            "docker",
            "exec",
            source,
            "curl",
            "-sS",
            "--max-time",
            "3",
            f"http://{target}:8080",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0, f"Isolation violation: {source} reached {target}:8080. stdout={result.stdout!r}"


@pytest.mark.usefixtures("_require_docker")
def test_session_container_cannot_ping_other_session() -> None:
    """From session A, ping session B → must fail (ICMP blocked)."""
    containers = _list_session_containers()
    if len(containers) < 2:
        pytest.skip(f"Need >=2 running session containers, found {len(containers)}")

    source = containers[0]
    target = containers[1]

    result = subprocess.run(
        [
            "docker",
            "exec",
            source,
            "ping",
            "-c",
            "1",
            "-W",
            "2",
            target,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0, f"Isolation violation: {source} can ping {target}. stdout={result.stdout!r}"
