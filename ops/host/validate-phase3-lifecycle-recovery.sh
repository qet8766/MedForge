#!/usr/bin/env bash
#
# Phase 3 session lifecycle and recovery validation.
# Combines runtime create/stop/snapshot witness with recovery-focused test lanes.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/ops/host/lib/remote-external.sh"
source "${ROOT_DIR}/ops/host/lib/phase-runner.sh"
PHASE_ID="phase3-lifecycle-recovery"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/docs/evidence/$(date -u +%F)}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.md}"
LOG_FILE="${LOG_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.log}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/compose/.env}"
DOMAIN="${DOMAIN:-}"
VALIDATE_PARALLEL="${VALIDATE_PARALLEL:-1}"
PYTEST_WORKERS="${PYTEST_WORKERS:-2}"
PYTEST_DIST_MODE="${PYTEST_DIST_MODE:-loadscope}"

PHASE_STATUS="INCONCLUSIVE"

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phase3-lifecycle-recovery.sh

Optional env:
  ENV_FILE=deploy/compose/.env
  DOMAIN=<override>
  VALIDATE_PARALLEL=1  # set to 0 to force sequential checks
  PYTEST_WORKERS=2
  PYTEST_DIST_MODE=loadscope
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
  if [ "${PHASE_STATUS}" != "PASS" ] && [ -f "${EVIDENCE_FILE}" ]; then
    record "## Verdict"
    record "- phase: \`${PHASE_ID}\`"
    record "- status: FAIL"
    record "- log: \`${LOG_FILE}\`"
  fi
  exit "${exit_code}"
}
trap cleanup EXIT

validate_parallel_env() {
  case "${VALIDATE_PARALLEL}" in
    0|1)
      ;;
    *)
      echo "ERROR: VALIDATE_PARALLEL must be 0 or 1 (got '${VALIDATE_PARALLEL}')."
      exit 1
      ;;
  esac

  if [ "${VALIDATE_PARALLEL}" = "1" ]; then
    if ! [[ "${PYTEST_WORKERS}" =~ ^[0-9]+$ ]] || [ "${PYTEST_WORKERS}" -lt 1 ]; then
      echo "ERROR: PYTEST_WORKERS must be a positive integer (got '${PYTEST_WORKERS}')."
      exit 1
    fi
  fi
}

run_pytest_with_optional_parallel() {
  local -a test_paths=("$@")
  local -a pytest_args

  if [ "${VALIDATE_PARALLEL}" = "1" ] && python3 -c 'import xdist' >/dev/null 2>&1; then
    pytest_args=(-q -n "${PYTEST_WORKERS}" --dist "${PYTEST_DIST_MODE}")
  else
    if [ "${VALIDATE_PARALLEL}" = "1" ]; then
      echo "WARN: pytest-xdist unavailable in active venv; running pytest sequentially." >&2
    fi
    pytest_args=(-q)
  fi

  pytest "${pytest_args[@]}" "${test_paths[@]}"
}

run_runtime_core_witness() {
  local api_host api_base
  local cookie_jar create_json
  local signup_out login_out
  local create_code stop_code route_code
  local session_id slug proxy_code
  local email="phase3-runtime-${RUN_ID}@medforge.test"

  api_host="$(remote_external_api_host "${DOMAIN}")"
  api_base="https://${api_host}"
  cookie_jar="$(mktemp /tmp/phase3-runtime-cookie.XXXXXX)"
  create_json="$(mktemp /tmp/phase3-runtime-create.XXXXXX)"
  signup_out="$(mktemp /tmp/phase3-runtime-signup.XXXXXX)"
  login_out="$(mktemp /tmp/phase3-runtime-login.XXXXXX)"

  signup_code="$(curl -sS -o "${signup_out}" -w '%{http_code}' \
    -c "${cookie_jar}" \
    -H 'content-type: application/json' \
    -X POST "${api_base}/api/v2/auth/signup" \
    --data "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"
  if [ "${signup_code}" != "201" ] && [ "${signup_code}" != "409" ]; then
    echo "ERROR: phase3 runtime signup failed (code=${signup_code})"
    cat "${signup_out}" || true
    rm -f "${cookie_jar}" "${create_json}" "${signup_out}" "${login_out}"
    return 1
  fi
  if [ "${signup_code}" = "409" ]; then
    login_code="$(curl -sS -o "${login_out}" -w '%{http_code}' \
      -c "${cookie_jar}" -b "${cookie_jar}" \
      -H 'content-type: application/json' \
      -X POST "${api_base}/api/v2/auth/login" \
      --data "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"
    if [ "${login_code}" != "200" ]; then
      echo "ERROR: phase3 runtime login failed (code=${login_code})"
      cat "${login_out}" || true
      rm -f "${cookie_jar}" "${create_json}" "${signup_out}" "${login_out}"
      return 1
    fi
  fi

  create_code="$(curl -sS -o "${create_json}" -w '%{http_code}' \
    -b "${cookie_jar}" \
    -H 'content-type: application/json' \
    -X POST "${api_base}/api/v2/external/sessions" \
    --data '{}')"
  if [ "${create_code}" != "201" ]; then
    echo "ERROR: phase3 runtime create failed (code=${create_code})"
    cat "${create_json}" || true
    rm -f "${cookie_jar}" "${create_json}" "${signup_out}" "${login_out}"
    return 1
  fi

  session_id="$(python3 - <<'PY' "${create_json}"
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    print(json.load(f).get("data", {}).get("session", {}).get("id", ""))
PY
)"
  slug="$(python3 - <<'PY' "${create_json}"
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    print(json.load(f).get("data", {}).get("session", {}).get("slug", ""))
PY
)"
  if [ -z "${session_id}" ] || [ -z "${slug}" ]; then
    echo "ERROR: phase3 runtime create payload missing id/slug"
    cat "${create_json}" || true
    rm -f "${cookie_jar}" "${create_json}" "${signup_out}" "${login_out}"
    return 1
  fi

  route_code=000
  for _ in $(seq 1 20); do
    route_code="$(curl -sS -o /tmp/phase3-runtime-route.out -w '%{http_code}' \
      -b "${cookie_jar}" \
      --max-time 10 \
      "https://$(remote_external_session_host "${slug}" "${DOMAIN}")" || echo 000)"
    if [ "${route_code}" = "200" ] || [ "${route_code}" = "302" ]; then
      break
    fi
    sleep 2
  done
  if [ "${route_code}" != "200" ] && [ "${route_code}" != "302" ]; then
    echo "ERROR: phase3 runtime wildcard routing failed (last=${route_code})"
    rm -f "${cookie_jar}" "${create_json}" "${signup_out}" "${login_out}"
    return 1
  fi

  stop_code="$(curl -sS -o /tmp/phase3-runtime-stop.out -w '%{http_code}' \
    -b "${cookie_jar}" \
    -X POST "${api_base}/api/v2/external/sessions/${session_id}/stop")"
  if [ "${stop_code}" != "202" ]; then
    echo "ERROR: phase3 runtime stop failed (code=${stop_code})"
    rm -f "${cookie_jar}" "${create_json}" "${signup_out}" "${login_out}"
    return 1
  fi

  proxy_code=000
  for _ in $(seq 1 90); do
    proxy_code="$(curl -sS -o /tmp/phase3-runtime-proxy.out -w '%{http_code}' \
      -b "${cookie_jar}" \
      --max-time 10 \
      "https://$(remote_external_session_host "${slug}" "${DOMAIN}")" || echo 000)"
    if [ "${proxy_code}" = "404" ]; then
      break
    fi
    sleep 1
  done
  if [ "${proxy_code}" != "404" ]; then
    echo "ERROR: phase3 runtime stop did not finalize (last wildcard code=${proxy_code})"
    rm -f "${cookie_jar}" "${create_json}" "${signup_out}" "${login_out}"
    return 1
  fi

  rm -f "${cookie_jar}" "${create_json}" "${signup_out}" "${login_out}"
}

run_lifecycle_recovery_tests() {
  cd "${ROOT_DIR}/apps/api"

  if [ ! -d ".venv" ]; then
    echo "ERROR: apps/api/.venv not found."
    return 1
  fi

  # shellcheck source=/dev/null
  . .venv/bin/activate

  run_pytest_with_optional_parallel \
    tests/test_api.py::test_session_create_rejects_client_supplied_exposure_field \
    tests/test_api.py::test_internal_session_create_requires_entitlement \
    tests/test_api.py::test_internal_session_create_with_entitlement_returns_running \
    tests/test_api.py::test_session_create_requires_auth \
    tests/test_api.py::test_session_create_external_returns_running \
    tests/test_api.py::test_session_create_enforces_user_limit \
    tests/test_api.py::test_session_create_exhausts_gpu_capacity \
    tests/test_api.py::test_session_stop_owner_marks_stopping_and_is_idempotent \
    tests/test_api.py::test_session_stop_forbidden_for_other_user \
    tests/test_api.py::test_session_stop_terminal_row_returns_current_state \
    tests/test_api.py::test_session_create_runtime_failure_marks_error \
    tests/test_concurrency.py \
    tests/test_session_recovery.py \
    tests/test_poller_sla.py \
    tests/test_chaos.py \
    tests/test_main_lifecycle.py::test_healthz_returns_503_when_recovery_enabled_without_live_thread \
    tests/test_main_lifecycle.py::test_healthz_returns_200_with_live_recovery_thread
}

main() {
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
  fi

  if [ -z "${DOMAIN}" ]; then
    DOMAIN="$(remote_read_env_value "${ENV_FILE}" DOMAIN)"
  fi
  remote_require_domain "${DOMAIN}"
  validate_parallel_env

  require_cmd bash
  require_cmd curl
  require_cmd python3

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 3 Lifecycle and Recovery Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase3-lifecycle-recovery.sh\`"
    echo ""
    echo "Runtime:"
    echo "- run id: \`${RUN_ID}\`"
    echo "- external domain: \`${DOMAIN}\`"
    echo "- validate parallel: \`${VALIDATE_PARALLEL}\`"
    if [ "${VALIDATE_PARALLEL}" = "1" ]; then
      echo "- pytest workers: \`${PYTEST_WORKERS}\`"
      echo "- pytest dist mode: \`${PYTEST_DIST_MODE}\`"
    fi
    echo ""
  } >"${EVIDENCE_FILE}"

  run_check_timed "Runtime Core Witness (Create/Stop/Snapshot)" "run_runtime_core_witness"
  run_check_timed "Lifecycle and Recovery Test Lanes" "run_lifecycle_recovery_tests"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
