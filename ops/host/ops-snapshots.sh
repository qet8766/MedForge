#!/usr/bin/env bash
#
# MF-102: List/inspect ZFS snapshots for a session slug or user.
#
# Usage:
#   bash ops/host/ops-snapshots.sh                 # list all session snapshots
#   bash ops/host/ops-snapshots.sh <session-slug>  # filter by slug
#   bash ops/host/ops-snapshots.sh --user <uuid>   # filter by user ID
#
# Optional env:
#   ZFS_ROOT=tank/medforge/workspaces

set -euo pipefail

ZFS_ROOT="${ZFS_ROOT:-tank/medforge/workspaces}"

usage() {
  cat <<'USAGE'
Usage: bash ops/host/ops-snapshots.sh [options]

Options:
  <slug>           Filter snapshots by session slug (8-char)
  --user <uuid>    Filter snapshots by user UUID prefix
  --all            Show all snapshots under ZFS_ROOT
  -h, --help       Show this help message

Examples:
  bash ops/host/ops-snapshots.sh abc12345
  bash ops/host/ops-snapshots.sh --user 00000000-0000-0000
USAGE
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${cmd}"
    exit 1
  fi
}

list_all_snapshots() {
  echo "=== All ZFS snapshots under ${ZFS_ROOT} ==="
  echo ""
  zfs list -t snapshot -r "${ZFS_ROOT}" -o name,creation,used,refer -s creation 2>/dev/null || echo "(no snapshots found)"
}

list_snapshots_by_filter() {
  local filter="$1"
  local label="$2"

  echo "=== ZFS snapshots matching ${label}: ${filter} ==="
  echo ""
  zfs list -t snapshot -r "${ZFS_ROOT}" -o name,creation,used,refer -s creation 2>/dev/null \
    | grep -i "${filter}" || echo "(no matching snapshots found)"
}

main() {
  require_cmd zfs

  if [ "$#" -eq 0 ]; then
    list_all_snapshots
    return
  fi

  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --all)
      list_all_snapshots
      ;;
    --user)
      if [ -z "${2:-}" ]; then
        echo "ERROR: --user requires a UUID argument"
        usage
        exit 1
      fi
      list_snapshots_by_filter "$2" "user"
      ;;
    *)
      list_snapshots_by_filter "$1" "slug/session"
      ;;
  esac
}

main "$@"
