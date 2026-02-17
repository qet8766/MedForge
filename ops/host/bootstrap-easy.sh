#!/usr/bin/env bash
#
# One-command host bootstrap for MedForge alpha.
# Defaults target production (physical POOL_DISKS required).
#
# Usage:
#   sudo bash ops/host/bootstrap-easy.sh
#
# Optional env:
#   POOL_NAME=tank
#   POOL_DISKS="/dev/sdb /dev/sdc"     # physical disks (optional)
#   USE_LOOPBACK_IF_NO_DISKS=false     # default false; set true for dev/CI
#   LOOPBACK_FILE=/var/tmp/medforge-tank.img
#   LOOPBACK_SIZE_GB=40
#   BUILD_PACK_IMAGE=true              # default true
#   WORKSPACE_USER=<username>          # default: invoking user

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

POOL_NAME="${POOL_NAME:-tank}"
POOL_DISKS="${POOL_DISKS:-}"
USE_LOOPBACK_IF_NO_DISKS="${USE_LOOPBACK_IF_NO_DISKS:-false}"
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
    run_sudo zpool create \
      -o ashift=12 \
      -o autotrim=on \
      -O compression=lz4 \
      -O atime=off \
      -O xattr=sa \
      -O dnodesize=auto \
      -O normalization=formD \
      -O relatime=on \
      "${POOL_NAME}" ${POOL_DISKS}
    return
  fi

  if [ "${USE_LOOPBACK_IF_NO_DISKS}" != "true" ]; then
    echo "ERROR: no ZFS pool found and POOL_DISKS is empty."
    echo "For production, set POOL_DISKS to physical disk paths."
    echo "For dev/CI, set USE_LOOPBACK_IF_NO_DISKS=true."
    exit 1
  fi

  echo "Creating loopback-backed pool '${POOL_NAME}' at ${LOOPBACK_FILE} (${LOOPBACK_SIZE_GB}G)..."
  run_sudo truncate -s "${LOOPBACK_SIZE_GB}G" "${LOOPBACK_FILE}"
  run_sudo zpool create -f \
    -o ashift=12 \
    -o autotrim=on \
    -O compression=lz4 \
    -O atime=off \
    -O xattr=sa \
    -O dnodesize=auto \
    -O normalization=formD \
    -O relatime=on \
    "${POOL_NAME}" "${LOOPBACK_FILE}"
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

ensure_zfs_tuning() {
  local arc_max=34359738368  # 32 GiB

  if ! grep -q "zfs_arc_max" /etc/modprobe.d/zfs.conf 2>/dev/null; then
    echo "options zfs zfs_arc_max=${arc_max}" | run_sudo tee /etc/modprobe.d/zfs.conf >/dev/null
  fi
  if [ -w /sys/module/zfs/parameters/zfs_arc_max ]; then
    echo "${arc_max}" | run_sudo tee /sys/module/zfs/parameters/zfs_arc_max >/dev/null
  fi

  if [ ! -f /etc/cron.d/zfs-scrub ]; then
    echo "0 2 * * 0 root /usr/sbin/zpool scrub ${POOL_NAME}" \
      | run_sudo tee /etc/cron.d/zfs-scrub >/dev/null
  fi

  echo "ZFS tuning applied (ARC max 32 GiB, weekly scrub)."
}

ensure_docker_data_root() {
  local daemon_json="/etc/docker/daemon.json"
  local data_root="/tank/docker"

  if [ -f "${daemon_json}" ] && grep -q '"data-root"' "${daemon_json}"; then
    echo "Docker data-root already configured."
    return
  fi

  if [ ! -f "${daemon_json}" ]; then
    echo "{\"data-root\": \"${data_root}\"}" | run_sudo tee "${daemon_json}" >/dev/null
  elif command -v jq >/dev/null 2>&1; then
    local tmp
    # shellcheck disable=SC2016
    tmp="$(run_sudo jq --arg dr "${data_root}" '. + {"data-root": $dr}' "${daemon_json}")"
    echo "${tmp}" | run_sudo tee "${daemon_json}" >/dev/null
  else
    echo "WARNING: jq not available. Manually add \"data-root\": \"${data_root}\" to ${daemon_json}"
    return
  fi

  run_sudo systemctl restart docker
  echo "Docker data-root set to ${data_root}."
}

ensure_networks_and_firewall() {
  if ! run_docker network inspect medforge-external-sessions >/dev/null 2>&1; then
    run_docker network create --subnet=172.30.0.0/24 medforge-external-sessions >/dev/null
    echo "Created Docker network medforge-external-sessions."
  fi
  run_sudo bash "${ROOT_DIR}/ops/network/firewall-setup.sh"
}

ensure_compose_env() {
  if [ ! -f "${ROOT_DIR}/deploy/compose/.env" ]; then
    cp "${ROOT_DIR}/deploy/compose/.env.example" "${ROOT_DIR}/deploy/compose/.env"
    echo "Created deploy/compose/.env from .env.example"
  fi
}

build_pack_image() {
  if [ "${BUILD_PACK_IMAGE}" != "true" ]; then
    echo "Skipping pack image build (BUILD_PACK_IMAGE=${BUILD_PACK_IMAGE})."
    return
  fi
  run_docker build -t medforge-pack-default:local -f "${ROOT_DIR}/deploy/packs/default/Dockerfile" "${ROOT_DIR}/deploy/packs/default"
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
  run_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y zfsutils-linux iptables jq

  ensure_nvidia_toolkit
  ensure_bridge_netfilter
  ensure_zfs_pool
  ensure_zfs_datasets
  ensure_workspace_permissions
  ensure_zfs_tuning
  ensure_docker_data_root
  ensure_networks_and_firewall
  ensure_compose_env
  build_pack_image

  echo ""
  echo "Bootstrap complete."
  echo "Next:"
  echo "  1) Edit deploy/compose/.env secrets and domain settings."
  echo "  2) Start stack: docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build"
  echo "  3) Validate phase flow (remote-external canonical): bash ops/host/validate-phases-all.sh"
  echo "     (or run phase 4 only: bash ops/host/validate-phase4-routing-e2e.sh)"
}

main "$@"
