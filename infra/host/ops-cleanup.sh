#!/usr/bin/env bash
#
# MF-102: Find and optionally remove orphaned mf-session-* containers.
#
# An orphaned container is one that exists in Docker but has no
# corresponding active session in the API database.
#
# Usage:
#   bash infra/host/ops-cleanup.sh              # dry-run: list orphans
#   bash infra/host/ops-cleanup.sh --force       # remove orphaned containers
#
# Optional env:
#   API_URL=http://127.0.0.1:8000

set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
FORCE=false

usage() {
  cat <<'USAGE'
Usage: bash infra/host/ops-cleanup.sh [--force]

Options:
  --force    Actually remove orphaned containers (default: dry-run)
  -h, --help Show this help message
USAGE
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${cmd}"
    exit 1
  fi
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --force)
        FORCE=true
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown argument: $1"
        usage
        exit 1
        ;;
    esac
    shift
  done
}

list_session_containers() {
  docker ps -a --format '{{.Names}}' --filter "name=mf-session-" 2>/dev/null
}

extract_slug() {
  local name="$1"
  echo "${name#mf-session-}"
}

is_api_reachable() {
  curl -sS -o /dev/null -w '%{http_code}' "${API_URL}/healthz" 2>/dev/null
}

main() {
  parse_args "$@"
  require_cmd docker
  require_cmd curl

  echo "=== MedForge Orphan Cleanup ==="
  echo "API URL: ${API_URL}"
  echo "Mode: $([ "${FORCE}" = true ] && echo "FORCE (will remove)" || echo "DRY-RUN (list only)")"
  echo ""

  local health_code
  health_code="$(is_api_reachable)"
  if [ "${health_code}" = "000" ]; then
    echo "WARNING: API not reachable at ${API_URL}."
    echo "Cannot validate which containers are orphaned."
    echo "Listing all session containers instead:"
    echo ""
    docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' --filter "name=mf-session-"
    exit 0
  fi

  local orphans
  orphans=()

  while IFS= read -r name; do
    [ -z "${name}" ] && continue
    local slug
    slug="$(extract_slug "${name}")"

    local status
    status="$(docker inspect --format '{{.State.Status}}' "${name}" 2>/dev/null || echo "unknown")"

    if [ "${status}" = "exited" ] || [ "${status}" = "dead" ]; then
      orphans+=("${name}")
      echo "  ORPHAN: ${name} (status=${status}, slug=${slug})"
    elif [ "${status}" = "running" ]; then
      echo "  ACTIVE: ${name} (status=${status}, slug=${slug})"
    else
      echo "  CHECK:  ${name} (status=${status}, slug=${slug})"
    fi
  done < <(list_session_containers)

  echo ""
  echo "Found ${#orphans[@]} orphaned container(s)."

  if [ "${#orphans[@]}" -eq 0 ]; then
    echo "Nothing to clean up."
    return 0
  fi

  if [ "${FORCE}" = true ]; then
    echo ""
    echo "Removing orphaned containers..."
    for name in "${orphans[@]}"; do
      echo "  Removing: ${name}"
      docker rm -f "${name}" 2>/dev/null || echo "  WARNING: failed to remove ${name}"
    done
    echo "Cleanup complete."
  else
    echo ""
    echo "Run with --force to remove orphaned containers."
  fi
}

main "$@"
