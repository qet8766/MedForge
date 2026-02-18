#!/usr/bin/env bash
#
# Phase 0 host infrastructure validation.
# Verifies GPU runtime, ZFS primitives, Docker networks, wildcard DNS, and strict TLS.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${ROOT_DIR}/ops/host/lib/remote-external.sh"
source "${ROOT_DIR}/ops/host/lib/phase-runner.sh"
PHASE_ID="phase0-host"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/docs/evidence/$(date -u +%F)}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.md}"
LOG_FILE="${LOG_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.log}"

ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/compose/.env}"
ZPOOL_NAME="${ZPOOL_NAME:-tank}"
ZFS_WORKSPACE_ROOT="${ZFS_WORKSPACE_ROOT:-tank/medforge/workspaces}"
DOMAIN="${DOMAIN:-}"
PACK_IMAGE="${PACK_IMAGE:-}"

PHASE_STATUS="INCONCLUSIVE"
TMP_DATASET=""
TMP_DATASET_CREATED=false

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phase0-host.sh

Optional env:
  DOMAIN=<medforge domain>
  PACK_IMAGE=<digest-pinned image ref>
  ZPOOL_NAME=tank
  ZFS_WORKSPACE_ROOT=tank/medforge/workspaces
  EVIDENCE_DIR=docs/evidence/<date>
  EVIDENCE_FILE=<explicit markdown path>
  LOG_FILE=<explicit log path>
USAGE
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${cmd}"
    exit 1
  fi
}

record() {
  local line="$1"
  printf "%s\n" "${line}" >>"${EVIDENCE_FILE}"
}

cleanup() {
  local exit_code=$?

  if [ "${TMP_DATASET_CREATED}" = true ] && [ -n "${TMP_DATASET}" ]; then
    sudo -n zfs destroy -r "${TMP_DATASET}" >/dev/null 2>&1 || true
  fi

  if [ "${PHASE_STATUS}" != "PASS" ] && [ -f "${EVIDENCE_FILE}" ]; then
    record "## Verdict"
    record "- phase: \`${PHASE_ID}\`"
    record "- status: FAIL"
    record "- log: \`${LOG_FILE}\`"
  fi

  exit "${exit_code}"
}
trap cleanup EXIT

gpu_host_visibility() {
  nvidia-smi -L
  nvidia-smi
}

gpu_vram_probe() {
  local vram
  vram="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -n1)"
  echo "GPU VRAM: ${vram}"
  if [ -z "${vram}" ]; then
    echo "ERROR: could not query GPU VRAM"
    return 1
  fi
}

gpu_container_runtime() {
  docker run --rm --gpus all --entrypoint nvidia-smi "${PACK_IMAGE}"
}

zfs_pool_health() {
  zpool list
  zpool status "${ZPOOL_NAME}"
  sudo -n zfs list "${ZFS_WORKSPACE_ROOT}"
}

zfs_write_read_snapshot_probe() {
  local mountpoint probe readback
  local tmp_ds="${ZFS_WORKSPACE_ROOT}/phase0-validation-${RUN_ID}"
  local tmp_snap="${tmp_ds}@phase0-${RUN_ID}"

  sudo -n zfs create -p "${tmp_ds}"
  TMP_DATASET="${tmp_ds}"
  TMP_DATASET_CREATED=true

  mountpoint="$(sudo -n zfs get -H -o value mountpoint "${tmp_ds}")"
  probe="phase0-${RUN_ID}"
  printf "%s\n" "${probe}" | sudo -n tee "${mountpoint}/probe.txt" >/dev/null
  readback="$(sudo -n cat "${mountpoint}/probe.txt")"
  if [ "${readback}" != "${probe}" ]; then
    echo "ERROR: ZFS readback mismatch"
    return 1
  fi

  sudo -n zfs snapshot "${tmp_snap}"
  sudo -n zfs list -t snapshot "${tmp_snap}"

  sudo -n zfs destroy "${tmp_snap}"
  sudo -n zfs destroy "${tmp_ds}"
  TMP_DATASET_CREATED=false
}

zfs_snapshot_restore_probe() {
  local mountpoint original overwritten restored
  local tmp_ds="${ZFS_WORKSPACE_ROOT}/phase0-restore-${RUN_ID}"
  local tmp_snap="${tmp_ds}@restore-test"

  sudo -n zfs create -p "${tmp_ds}"
  TMP_DATASET="${tmp_ds}"
  TMP_DATASET_CREATED=true

  mountpoint="$(sudo -n zfs get -H -o value mountpoint "${tmp_ds}")"

  original="restore-original-${RUN_ID}"
  printf "%s\n" "${original}" | sudo -n tee "${mountpoint}/restore.txt" >/dev/null
  sudo -n zfs snapshot "${tmp_snap}"

  overwritten="overwritten-data"
  printf "%s\n" "${overwritten}" | sudo -n tee "${mountpoint}/restore.txt" >/dev/null

  sudo -n zfs rollback "${tmp_snap}"

  restored="$(sudo -n cat "${mountpoint}/restore.txt")"
  if [ "${restored}" != "${original}" ]; then
    echo "ERROR: ZFS rollback mismatch: expected '${original}', got '${restored}'"
    sudo -n zfs destroy "${tmp_snap}" || true
    sudo -n zfs destroy "${tmp_ds}" || true
    TMP_DATASET_CREATED=false
    return 1
  fi
  echo "ZFS snapshot restore verified: data matches original after rollback"

  sudo -n zfs destroy "${tmp_snap}"
  sudo -n zfs destroy "${tmp_ds}"
  TMP_DATASET_CREATED=false
}

docker_network_check() {
  local net
  for net in medforge-external-sessions medforge-internal-sessions; do
    if ! docker network inspect "${net}" >/dev/null 2>&1; then
      echo "ERROR: docker network '${net}' not found"
      return 1
    fi
    echo "Docker network '${net}' exists"
  done
}

dns_resolution() {
  remote_dns_check_bundle "${DOMAIN}" "phase0check"
}

tls_probe() {
  local web_host api_host

  web_host="$(remote_external_web_host "${DOMAIN}")"
  api_host="$(remote_external_api_host "${DOMAIN}")"

  curl -fsS "https://${web_host}" >/dev/null
  curl -fsS "https://${api_host}/healthz" >/dev/null

  remote_tls_verify_host "${web_host}"
  remote_tls_verify_host "${api_host}"
}

main() {
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
  fi

  require_cmd curl
  require_cmd docker
  require_cmd dig
  require_cmd nvidia-smi
  require_cmd openssl
  require_cmd rg
  require_cmd sudo
  require_cmd zfs
  require_cmd zpool

  if ! sudo -n true >/dev/null 2>&1; then
    echo "ERROR: this script requires passwordless sudo (sudo -n)."
    exit 1
  fi

  if [ -z "${DOMAIN}" ]; then
    DOMAIN="$(remote_read_env_value "${ENV_FILE}" DOMAIN)"
  fi
  if [ -z "${PACK_IMAGE}" ]; then
    PACK_IMAGE="$(remote_read_env_value "${ENV_FILE}" PACK_IMAGE)"
  fi

  if [ -z "${DOMAIN}" ]; then
    echo "ERROR: DOMAIN is required (env or ${ENV_FILE})."
    exit 1
  fi
  if [ -z "${PACK_IMAGE}" ]; then
    echo "ERROR: PACK_IMAGE is required (env or ${ENV_FILE})."
    exit 1
  fi

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 0 Host Infrastructure Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase0-host.sh\`"
    echo ""
    echo "Runtime:"
    echo "- domain: \`${DOMAIN}\`"
    echo "- pack image: \`${PACK_IMAGE}\`"
    echo "- zpool: \`${ZPOOL_NAME}\`"
    echo "- workspace root: \`${ZFS_WORKSPACE_ROOT}\`"
    echo "- run id: \`${RUN_ID}\`"
    echo ""
  } >"${EVIDENCE_FILE}"

  run_check_timed "GPU Host Visibility" "gpu_host_visibility"
  run_check_timed "GPU VRAM Probe" "gpu_vram_probe"
  run_check_timed "GPU Runtime In Container" "gpu_container_runtime"
  run_check_timed "ZFS Pool Health" "zfs_pool_health"
  run_check_timed "ZFS Write Read Snapshot Probe" "zfs_write_read_snapshot_probe"
  run_check_timed "ZFS Snapshot Restore Probe" "zfs_snapshot_restore_probe"
  run_check_timed "Docker Network Existence" "docker_network_check"
  run_check_timed "External DNS Resolution" "dns_resolution"
  run_check_timed "Strict TLS Validation" "tls_probe"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
