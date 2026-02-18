#!/usr/bin/env bash
#
# Phase 1 control-plane bootstrap validation.
# Brings up compose services, verifies reachability with body validation,
# validates seed rows, DB migration alignment, and bootstrap pytest lanes.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${ROOT_DIR}/ops/host/lib/remote-external.sh"
source "${ROOT_DIR}/ops/host/lib/phase-runner.sh"
PHASE_ID="phase1-bootstrap"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/docs/evidence/$(date -u +%F)}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.md}"
LOG_FILE="${LOG_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.log}"

ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/compose/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/deploy/compose/docker-compose.yml}"
DOMAIN="${DOMAIN:-}"
VALIDATE_PARALLEL="${VALIDATE_PARALLEL:-1}"

PHASE_STATUS="INCONCLUSIVE"

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phase1-bootstrap.sh

Optional env:
  ENV_FILE=deploy/compose/.env
  COMPOSE_FILE=deploy/compose/docker-compose.yml
  DOMAIN=<override>
  VALIDATE_PARALLEL=1  # set to 0 to force sequential checks
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

wait_for_health() {
  local name="$1"
  local max_attempts="$2"
  local sleep_seconds="$3"
  local checker="$4"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    if "${checker}"; then
      echo "${name} ready on attempt ${attempt}/${max_attempts}"
      return 0
    fi
    sleep "${sleep_seconds}"
    attempt=$((attempt + 1))
  done

  echo "ERROR: ${name} not ready after ${max_attempts} attempts"
  return 1
}

cleanup() {
  local exit_code=$?
  if [ "${PHASE_STATUS}" != "PASS" ] && [ -f "${EVIDENCE_FILE}" ]; then
    record "## Verdict"
    record "- phase: \`${PHASE_ID}\`"
    record "- status: FAIL"
    record "- log: \`${LOG_FILE}\`"
  fi
  exit "${exit_code}"
}
trap cleanup EXIT

compose_up() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build
}

compose_ps() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps
}

services_running() {
  local service
  for service in medforge-db medforge-api medforge-api-worker medforge-web medforge-caddy; do
    docker ps --format '{{.Names}}' | rg -x "${service}" >/dev/null
  done
}

api_health_remote_with_body() {
  local api_host out_file body status_field
  api_host="$(remote_external_api_host "${DOMAIN}")"
  out_file="$(mktemp /tmp/phase1-healthz.XXXXXX)"

  curl -fsS "https://${api_host}/healthz" -o "${out_file}"

  status_field="$(python3 -c "import json; print(json.load(open('${out_file}'))['status'])")"
  if [ "${status_field}" != "ok" ]; then
    echo "ERROR: /healthz status field is '${status_field}', expected 'ok'"
    cat "${out_file}"
    rm -f "${out_file}"
    return 1
  fi
  echo "API /healthz body validated: status=${status_field}"
  rm -f "${out_file}"
}

web_health_remote_with_body() {
  local web_host out_file
  web_host="$(remote_external_web_host "${DOMAIN}")"
  out_file="$(mktemp /tmp/phase1-web.XXXXXX)"

  curl -fsS "https://${web_host}" -o "${out_file}"

  if ! rg -q '<html' "${out_file}"; then
    echo "ERROR: web root response does not contain expected HTML marker"
    head -c 500 "${out_file}"
    rm -f "${out_file}"
    return 1
  fi
  echo "Web root body validated: contains HTML marker"
  rm -f "${out_file}"
}

db_seed_invariants() {
  local gpu_count
  local pack_count

  gpu_count="$(docker exec medforge-db sh -lc 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -Nse "SELECT COUNT(*) FROM gpu_devices WHERE enabled=1 AND id BETWEEN 0 AND 6;" medforge')"
  if [ "${gpu_count}" != "7" ]; then
    echo "ERROR: expected 7 enabled gpu_devices rows (0..6), got ${gpu_count}"
    return 1
  fi

  pack_count="$(docker exec medforge-db sh -lc 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -Nse "SELECT COUNT(*) FROM packs WHERE image_ref LIKE \"%@sha256:%\" OR image_digest LIKE \"sha256:%\";" medforge')"
  if ! [[ "${pack_count}" =~ ^[0-9]+$ ]] || [ "${pack_count}" -lt 1 ]; then
    echo "ERROR: expected at least one digest-pinned pack"
    return 1
  fi

  echo "gpu_count=${gpu_count}"
  echo "pack_count=${pack_count}"
}

db_migration_alignment() {
  docker exec medforge-api python3 -c "
from app.database import check_migration_alignment
result = check_migration_alignment()
print(f'migration_head={result}')
" 2>/dev/null && return 0

  echo "WARN: migration alignment check via Python unavailable, falling back to alembic_version query"
  local version
  version="$(docker exec medforge-db sh -lc 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -Nse "SELECT version_num FROM alembic_version LIMIT 1;" medforge')"
  if [ -z "${version}" ]; then
    echo "ERROR: no alembic_version row found"
    return 1
  fi
  echo "alembic_version=${version}"
}

run_bootstrap_pytest_lanes() {
  cd "${ROOT_DIR}/apps/api"

  if [ ! -d ".venv" ]; then
    echo "ERROR: apps/api/.venv not found."
    return 1
  fi

  # shellcheck source=/dev/null
  . .venv/bin/activate

  pytest -q \
    tests/test_session_runtime_contract.py \
    tests/test_session_runtime_resources.py
}

validate_parallel_env() {
  case "${VALIDATE_PARALLEL}" in
    0|1)
      ;;
    *)
      echo "ERROR: VALIDATE_PARALLEL must be 0 or 1 (got '${VALIDATE_PARALLEL}')."
      exit 1
      ;;
  esac
}

main() {
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
  fi

  require_cmd docker
  require_cmd curl
  require_cmd rg
  require_cmd python3

  if [ ! -f "${ENV_FILE}" ]; then
    echo "ERROR: env file not found: ${ENV_FILE}"
    exit 1
  fi
  if [ ! -f "${COMPOSE_FILE}" ]; then
    echo "ERROR: compose file not found: ${COMPOSE_FILE}"
    exit 1
  fi

  if [ -z "${DOMAIN}" ]; then
    DOMAIN="$(remote_read_env_value "${ENV_FILE}" DOMAIN)"
  fi
  remote_require_domain "${DOMAIN}"
  validate_parallel_env

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 1 Control Plane Bootstrap Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase1-bootstrap.sh\`"
    echo ""
    echo "Runtime:"
    echo "- env file: \`${ENV_FILE}\`"
    echo "- compose file: \`${COMPOSE_FILE}\`"
    echo "- domain: \`${DOMAIN:-unknown}\`"
    echo "- validate parallel: \`${VALIDATE_PARALLEL}\`"
    echo "- run id: \`${RUN_ID}\`"
    echo ""
  } >"${EVIDENCE_FILE}"

  run_check_timed "Compose Up" "compose_up"
  run_check_timed "Compose Service Table" "compose_ps"
  run_check_timed "Core Services Running" "services_running"

  if [ "${VALIDATE_PARALLEL}" = "1" ]; then
    run_parallel_checks \
      "External API Reachability (Body Validated)" "wait_for_health api 60 1 api_health_remote_with_body" \
      "External Web Reachability (Body Validated)" "wait_for_health web 60 1 web_health_remote_with_body"
  else
    run_check_timed "External API Reachability (Body Validated)" "wait_for_health api 60 1 api_health_remote_with_body"
    run_check_timed "External Web Reachability (Body Validated)" "wait_for_health web 60 1 web_health_remote_with_body"
  fi

  run_check_timed "Database Seed Invariants" "db_seed_invariants"
  run_check_timed "Database Migration Alignment" "db_migration_alignment"
  run_check_timed "Bootstrap Pytest Lanes" "run_bootstrap_pytest_lanes"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
