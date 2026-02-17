#!/usr/bin/env bash
#
# MF-102: Trigger manual session reconciliation.
#
# Runs a one-shot reconciliation pass by calling the API lifespan
# reconciliation logic directly via a helper script, or by restarting
# the API service (which runs reconcile_on_startup automatically).
#
# Usage:
#   bash ops/host/ops-reconcile.sh
#
# Optional env:
#   API_URL=https://api.medforge.<DOMAIN> — API base URL for health check
#   DOMAIN=<root-domain>
#   COMPOSE_ENV=deploy/compose/.env — Path to compose env file
#   COMPOSE_FILE=deploy/compose/docker-compose.yml

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REMOTE_PUBLIC_LIB="${ROOT_DIR}/ops/host/lib/remote-public.sh"
API_URL="${API_URL:-}"
COMPOSE_ENV="${COMPOSE_ENV:-${ROOT_DIR}/deploy/compose/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/deploy/compose/docker-compose.yml}"

if [ ! -f "${REMOTE_PUBLIC_LIB}" ]; then
  echo "ERROR: missing helper library: ${REMOTE_PUBLIC_LIB}"
  exit 1
fi
# shellcheck disable=SC1091
# shellcheck source=ops/host/lib/remote-public.sh
source "${REMOTE_PUBLIC_LIB}"

resolve_api_url() {
  local domain="${DOMAIN:-}"
  if [ -z "${domain}" ]; then
    domain="$(remote_read_env_value "${COMPOSE_ENV}" DOMAIN | tr -d '[:space:]')"
  fi
  if [ -z "${domain}" ]; then
    return 1
  fi
  printf "https://%s\n" "$(remote_public_api_host "${domain}")"
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${cmd}"
    exit 1
  fi
}

check_api_health() {
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "${API_URL}/healthz" 2>/dev/null || echo "000")"
  echo "${code}"
}

restart_api_service() {
  echo "Restarting medforge-api to trigger boot reconciliation..."
  docker compose --env-file "${COMPOSE_ENV}" -f "${COMPOSE_FILE}" restart medforge-api
  echo "Waiting for API to become healthy..."

  for _ in $(seq 1 60); do
    local code
    code="$(check_api_health)"
    if [ "${code}" = "200" ]; then
      echo "API healthy (200). Reconciliation complete."
      return 0
    fi
    sleep 1
  done

  echo "WARNING: API did not return 200 within 60 seconds."
  echo "Last health check: $(check_api_health)"
  return 1
}

show_active_sessions() {
  echo ""
  echo "Active sessions (from docker):"
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' --filter "name=mf-session-" 2>/dev/null || echo "  (no session containers found)"
}

main() {
  require_cmd curl
  require_cmd docker

  if [ -z "${API_URL}" ]; then
    if ! API_URL="$(resolve_api_url)"; then
      echo "ERROR: API_URL is required when DOMAIN is unavailable."
      echo "Set API_URL explicitly or configure DOMAIN in ${COMPOSE_ENV}."
      exit 1
    fi
  fi

  echo "=== MedForge Reconciliation ==="
  echo "API URL: ${API_URL}"
  echo "Compose file: ${COMPOSE_FILE}"
  echo ""

  local pre_health
  pre_health="$(check_api_health)"
  echo "Pre-reconcile health: ${pre_health}"

  if [ "${pre_health}" = "000" ]; then
    echo "ERROR: API is not reachable at ${API_URL}."
    echo "Is the compose stack running?"
    exit 1
  fi

  restart_api_service
  show_active_sessions
}

main "$@"
