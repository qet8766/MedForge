#!/usr/bin/env bash
#
# One-command host bootstrap for MedForge alpha.
# Safe defaults favor a local loopback ZFS pool when no physical disks are provided.
#
# Usage:
#   sudo bash infra/host/bootstrap-easy.sh
#
# Optional env:
#   POOL_NAME=tank
#   POOL_DISKS="/dev/sdb /dev/sdc"     # physical disks (optional)
#   USE_LOOPBACK_IF_NO_DISKS=true      # default true
#   LOOPBACK_FILE=/var/tmp/medforge-tank.img
#   LOOPBACK_SIZE_GB=40
#   BUILD_PACK_IMAGE=true              # default true
#   WORKSPACE_USER=<username>          # default: invoking user

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

POOL_NAME="${POOL_NAME:-tank}"
POOL_DISKS="${POOL_DISKS:-}"
USE_LOOPBACK_IF_NO_DISKS="${USE_LOOPBACK_IF_NO_DISKS:-true}"
LOOPBACK_FILE="${LOOPBACK_FILE:-/var/tmp/medforge-tank.img}"
LOOPBACK_SIZE_GB="${LOOPBACK_SIZE_GB:-40}"
BUILD_PACK_IMAGE="${BUILD_PACK_IMAGE:-true}"
WORKSPACE_USER="${WORKSPACE_USER:-${SUDO_USER:-$USER}}"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd"
    exit 1
  fi
}

run_sudo() {
  if [ "${EUID}" -eq 0 ]; then
    "$@"
    return
  fi
  sudo "$@"
}

run_docker() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
    return
  fi
  run_sudo docker "$@"
}

ensure_zfs_pool() {
  if zpool list "${POOL_NAME}" >/dev/null 2>&1; then
    echo "ZFS pool '${POOL_NAME}' already exists."
    return
  fi

  if [ -n "${POOL_DISKS}" ]; then
    echo "Creating pool '${POOL_NAME}' from POOL_DISKS..."
    # shellcheck disable=SC2086
    run_sudo zpool create -o ashift=12 "${POOL_NAME}" ${POOL_DISKS}
    return
  fi

  if [ "${USE_LOOPBACK_IF_NO_DISKS}" != "true" ]; then
    echo "ERROR: no ZFS pool found and POOL_DISKS is empty."
    echo "Set POOL_DISKS or USE_LOOPBACK_IF_NO_DISKS=true."
    exit 1
  fi

  echo "Creating loopback-backed pool '${POOL_NAME}' at ${LOOPBACK_FILE} (${LOOPBACK_SIZE_GB}G)..."
  run_sudo truncate -s "${LOOPBACK_SIZE_GB}G" "${LOOPBACK_FILE}"
  run_sudo zpool create -f "${POOL_NAME}" "${LOOPBACK_FILE}"
}

ensure_zfs_datasets() {
  local datasets=(
    "${POOL_NAME}/medforge"
    "${POOL_NAME}/medforge/workspaces"
    "${POOL_NAME}/medforge/system"
    "${POOL_NAME}/medforge/system/db"
  )

  for ds in "${datasets[@]}"; do
    if ! zfs list "${ds}" >/dev/null 2>&1; then
      run_sudo zfs create -p "${ds}"
      echo "Created dataset ${ds}"
    fi
  done

  run_sudo chown 999:999 "/${POOL_NAME}/medforge/system/db"
}

ensure_nvidia_toolkit() {
  if command -v nvidia-ctk >/dev/null 2>&1; then
    echo "nvidia-container-toolkit already installed."
  else
    echo "Installing nvidia-container-toolkit..."
    run_sudo rm -f /etc/apt/sources.list.d/nvidia-container-toolkit.list
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
      | run_sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
      | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
      | run_sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
    run_sudo apt-get update
    run_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-container-toolkit
  fi

  echo "Configuring Docker NVIDIA runtime..."
  run_sudo nvidia-ctk runtime configure --runtime=docker
  run_sudo systemctl restart docker
}

ensure_bridge_netfilter() {
  run_sudo modprobe br_netfilter
  run_sudo mkdir -p /etc/modules-load.d /etc/sysctl.d
  cat <<'EOF' | run_sudo tee /etc/modules-load.d/medforge-br-netfilter.conf >/dev/null
br_netfilter
EOF
  cat <<'EOF' | run_sudo tee /etc/sysctl.d/99-medforge-bridge.conf >/dev/null
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
  run_sudo sysctl -w net.bridge.bridge-nf-call-iptables=1 >/dev/null
  run_sudo sysctl -w net.bridge.bridge-nf-call-ip6tables=1 >/dev/null
}

ensure_workspace_permissions() {
  if id "${WORKSPACE_USER}" >/dev/null 2>&1; then
    run_sudo zfs allow -u "${WORKSPACE_USER}" create,destroy,mount,mountpoint,quota,snapshot "${POOL_NAME}/medforge/workspaces"
    echo "Granted ZFS workspace delegation to ${WORKSPACE_USER}"
  else
    echo "WARNING: user '${WORKSPACE_USER}' not found; skipped ZFS delegation."
  fi
}

ensure_networks_and_firewall() {
  if ! run_docker network inspect medforge-public-sessions >/dev/null 2>&1; then
    run_docker network create --subnet=172.30.0.0/24 medforge-public-sessions >/dev/null
    echo "Created Docker network medforge-public-sessions."
  fi
  run_sudo bash "${ROOT_DIR}/infra/firewall/setup.sh"
}

ensure_compose_env() {
  if [ ! -f "${ROOT_DIR}/infra/compose/.env" ]; then
    cp "${ROOT_DIR}/infra/compose/.env.example" "${ROOT_DIR}/infra/compose/.env"
    echo "Created infra/compose/.env from .env.example"
  fi
}

build_pack_image() {
  if [ "${BUILD_PACK_IMAGE}" != "true" ]; then
    echo "Skipping pack image build (BUILD_PACK_IMAGE=${BUILD_PACK_IMAGE})."
    return
  fi
  run_docker build -t medforge-pack-default:local -f "${ROOT_DIR}/infra/packs/default/Dockerfile" "${ROOT_DIR}/infra/packs/default"
}

main() {
  require_cmd curl
  require_cmd gpg
  require_cmd apt-get
  require_cmd zpool
  require_cmd zfs
  require_cmd docker

  echo "==> Installing base host packages..."
  run_sudo apt-get update
  run_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y zfsutils-linux iptables

  ensure_nvidia_toolkit
  ensure_bridge_netfilter
  ensure_zfs_pool
  ensure_zfs_datasets
  ensure_workspace_permissions
  ensure_networks_and_firewall
  ensure_compose_env
  build_pack_image

  echo ""
  echo "Bootstrap complete."
  echo "Next:"
  echo "  1) Edit infra/compose/.env secrets and domain settings."
  echo "  2) Start stack: docker compose --env-file infra/compose/.env -f infra/compose/docker-compose.yml up -d --build"
  echo "  3) Validate host flow: bash infra/host/validate-gate56.sh"
}

main "$@"
