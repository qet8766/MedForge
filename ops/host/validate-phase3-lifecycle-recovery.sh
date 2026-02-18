#!/usr/bin/env bash
#
# Phase 3 session lifecycle + E2E runtime validation.
# Full create/stop/snapshot witness with body validation, GPU probe,
# workspace write/read, /healthz monitoring, ZFS snapshot verification,
# and recovery-focused test lanes.

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
WITNESS_SESSION_ID=""
WITNESS_SLUG=""
WITNESS_COOKIE_JAR=""

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

  if [ -n "${WITNESS_SESSION_ID}" ] && [ -n "${WITNESS_COOKIE_JAR}" ] && [ -f "${WITNESS_COOKIE_JAR}" ]; then
    local api_host
    api_host="$(remote_external_api_host "${DOMAIN}")"
    curl -sS -X POST "https://${api_host}/api/v2/external/sessions/${WITNESS_SESSION_ID}/stop" \
      -b "${WITNESS_COOKIE_JAR}" >/dev/null 2>&1 || true
  fi
  if [ -n "${WITNESS_SLUG}" ]; then
    docker rm -f "mf-session-${WITNESS_SLUG}" >/dev/null 2>&1 || true
  fi
  if [ -n "${WITNESS_COOKIE_JAR}" ] && [ -f "${WITNESS_COOKIE_JAR}" ]; then
    rm -f "${WITNESS_COOKIE_JAR}" || true
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

wait_for_session_host_not_routing() {
  local host="$1"
  local cookie_token="$2"
  local timeout_seconds="${3:-120}"
  local code=""

  for _ in $(seq 1 "${timeout_seconds}"); do
    code="$(curl -sS -o /tmp/${PHASE_ID}-stopped.out -w '%{http_code}' \
      "https://${host}/" \
      -H "Cookie: medforge_session=${cookie_token}")"
    if [ "${code}" = "404" ]; then
      echo "${code}"
      return 0
    fi
    sleep 1
  done

  echo "ERROR: timed out waiting for session host ${host} to stop routing (last=${code})"
  return 1
}

wait_for_stop_snapshot() {
  local session_id="$1"
  local timeout_seconds="${2:-120}"
  local snapshot=""

  for _ in $(seq 1 "${timeout_seconds}"); do
    snapshot="$(sudo -n zfs list -t snapshot -H -o name | rg "tank/medforge/workspaces/.*/${session_id}@stop-" | tail -n1 || true)"
    if [ -n "${snapshot}" ]; then
      echo "${snapshot}"
      return 0
    fi
    sleep 1
  done

  echo "ERROR: timed out waiting for stop snapshot for session ${session_id}"
  return 1
}

run_healthz_check() {
  local api_host="$1"
  local label="$2"
  local out_file status_field

  out_file="$(mktemp /tmp/phase3-healthz-${label}.XXXXXX)"
  curl -fsS "https://${api_host}/healthz" -o "${out_file}"

  status_field="$(python3 -c "import json; print(json.load(open('${out_file}'))['status'])")"
  if [ "${status_field}" != "ok" ]; then
    echo "ERROR: /healthz status='${status_field}' (expected 'ok') during ${label}"
    rm -f "${out_file}"
    return 1
  fi
  echo "/healthz ${label}: status=${status_field}"
  rm -f "${out_file}"
}

run_runtime_core_witness() {
  local api_host api_base
  local cookie_jar create_json
  local signup_out login_out stop_out
  local create_code stop_code route_code
  local session_id slug session_status
  local email="phase3-runtime-${RUN_ID}@medforge.test"

  api_host="$(remote_external_api_host "${DOMAIN}")"
  api_base="https://${api_host}"
  cookie_jar="$(mktemp /tmp/phase3-runtime-cookie.XXXXXX)"
  create_json="$(mktemp /tmp/phase3-runtime-create.XXXXXX)"
  signup_out="$(mktemp /tmp/phase3-runtime-signup.XXXXXX)"
  login_out="$(mktemp /tmp/phase3-runtime-login.XXXXXX)"
  stop_out="$(mktemp /tmp/phase3-runtime-stop.XXXXXX)"
  WITNESS_COOKIE_JAR="${cookie_jar}"

  # Healthz before create
  run_healthz_check "${api_host}" "pre-create"

  signup_code="$(curl -sS -o "${signup_out}" -w '%{http_code}' \
    -c "${cookie_jar}" \
    -H 'content-type: application/json' \
    -X POST "${api_base}/api/v2/auth/signup" \
    --data "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"
  if [ "${signup_code}" != "201" ] && [ "${signup_code}" != "409" ]; then
    echo "ERROR: phase3 runtime signup failed (code=${signup_code})"
    cat "${signup_out}" || true
    rm -f "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
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
      rm -f "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
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
    rm -f "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
    return 1
  fi

  # Body validation on create response
  session_id="$(json_file_key "${create_json}" "data" | python3 -c "import json,sys; d=json.load(sys.stdin) if False else json.loads('{}'); print('')" 2>/dev/null || true)"
  session_id="$(python3 - <<'PY' "${create_json}"
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data = json.load(f)
session = data.get("data", {}).get("session", {})
print(session.get("id", ""))
PY
)"
  slug="$(python3 - <<'PY' "${create_json}"
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data = json.load(f)
session = data.get("data", {}).get("session", {})
print(session.get("slug", ""))
PY
)"
  session_status="$(python3 - <<'PY' "${create_json}"
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data = json.load(f)
session = data.get("data", {}).get("session", {})
print(session.get("status", ""))
PY
)"

  if [ -z "${session_id}" ] || [ -z "${slug}" ]; then
    echo "ERROR: phase3 runtime create payload missing id/slug"
    cat "${create_json}" || true
    rm -f "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
    return 1
  fi

  WITNESS_SESSION_ID="${session_id}"
  WITNESS_SLUG="${slug}"

  echo "Create response validated: id=${session_id}, slug=${slug}, status=${session_status}"
  if [ "${session_status}" != "starting" ] && [ "${session_status}" != "running" ]; then
    echo "ERROR: unexpected create status '${session_status}' (expected starting or running)"
    rm -f "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
    return 1
  fi

  # Wait for wildcard routing
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
    rm -f "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
    return 1
  fi

  # Healthz during session
  run_healthz_check "${api_host}" "during-session"

  # GPU probe in container
  local gpu_line
  gpu_line="$(docker exec "mf-session-${slug}" nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)"
  if [[ "${gpu_line}" != *NVIDIA* ]]; then
    echo "ERROR: GPU probe failed: ${gpu_line}"
    rm -f "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
    return 1
  fi
  echo "GPU in session: ${gpu_line}"

  # Workspace write/read
  local ws_line
  ws_line="$(docker exec "mf-session-${slug}" sh -lc 'echo alpha > /workspace/alpha.txt && cat /workspace/alpha.txt')"
  assert_eq "${ws_line}" "alpha" "workspace write/read"
  echo "Workspace write/read: ${ws_line}"

  # Stop session
  stop_code="$(curl -sS -o "${stop_out}" -w '%{http_code}' \
    -b "${cookie_jar}" \
    -X POST "${api_base}/api/v2/external/sessions/${session_id}/stop")"
  if [ "${stop_code}" != "202" ]; then
    echo "ERROR: phase3 runtime stop failed (code=${stop_code})"
    rm -f "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
    return 1
  fi

  # Body validation on stop response
  local stop_message
  stop_message="$(python3 - <<'PY' "${stop_out}"
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data = json.load(f)
print(data.get("data", {}).get("message", ""))
PY
)"
  assert_eq "${stop_message}" "Session stop requested." "stop response message"
  echo "Stop response validated: message='${stop_message}'"

  # Wait for routing to stop + ZFS snapshot
  local cookie_token host_a snapshot_result route_result
  cookie_token="$(cookie_token_from_jar "${cookie_jar}")"
  host_a="$(remote_external_session_host "${slug}" "${DOMAIN}")"

  local route_file snapshot_file
  route_file="$(mktemp /tmp/${PHASE_ID}-route.XXXXXX)"
  snapshot_file="$(mktemp /tmp/${PHASE_ID}-snapshot.XXXXXX)"

  wait_for_session_host_not_routing "${host_a}" "${cookie_token}" >"${route_file}" &
  local pid_route=$!
  wait_for_stop_snapshot "${session_id}" >"${snapshot_file}" &
  local pid_snapshot=$!

  set +e
  wait "${pid_route}"
  local rc_route=$?
  wait "${pid_snapshot}"
  local rc_snapshot=$?
  set -e

  if [ "${rc_route}" -ne 0 ] || [ "${rc_snapshot}" -ne 0 ]; then
    echo "ERROR: stop finalization failed (host_wait_rc=${rc_route}, snapshot_wait_rc=${rc_snapshot})"
    rm -f "${route_file}" "${snapshot_file}" "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
    return 1
  fi

  route_result="$(cat "${route_file}")"
  snapshot_result="$(cat "${snapshot_file}")"
  echo "Route finalized: ${route_result}"
  echo "ZFS snapshot: ${snapshot_result}"
  WITNESS_SESSION_ID=""

  # Healthz after stop
  run_healthz_check "${api_host}" "post-stop"

  rm -f "${route_file}" "${snapshot_file}" "${create_json}" "${signup_out}" "${login_out}" "${stop_out}"
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
    tests/test_api.py::test_session_by_id_returns_owner_session \
    tests/test_api.py::test_session_by_id_forbidden_for_other_user \
    tests/test_api.py::test_session_by_id_missing_returns_404 \
    tests/test_concurrency.py \
    tests/test_session_recovery.py \
    tests/test_poller_sla.py \
    tests/test_chaos.py \
    tests/test_invariants.py \
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
  require_cmd docker
  require_cmd python3
  require_cmd sudo
  require_cmd zfs

  if ! sudo -n true >/dev/null 2>&1; then
    echo "ERROR: this script requires passwordless sudo (sudo -n)."
    exit 1
  fi

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 3 Session Lifecycle + E2E Runtime Evidence ($(date -u +%F))"
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

  run_check_timed "Runtime Core Witness (Create/GPU/Workspace/Stop/Snapshot)" "run_runtime_core_witness"
  run_check_timed "Lifecycle and Recovery Test Lanes" "run_lifecycle_recovery_tests"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
