#!/usr/bin/env bash
#
# Phase 3 session lifecycle and recovery validation.
# Combines runtime create/stop/snapshot witness with recovery-focused test lanes.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/ops/host/lib/remote-public.sh"
PHASE_ID="phase3-lifecycle-recovery"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/docs/evidence/$(date -u +%F)}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.md}"
LOG_FILE="${LOG_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.log}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/compose/.env}"
DOMAIN="${DOMAIN:-}"

PHASE_STATUS="INCONCLUSIVE"

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phase3-lifecycle-recovery.sh

Optional env:
  ENV_FILE=deploy/compose/.env
  DOMAIN=<override>
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

run_check() {
  local name="$1"
  local cmd="$2"

  record "### ${name}"
  record ""
  record '```bash'
  record "${cmd}"
  record '```'

  if eval "${cmd}" >>"${LOG_FILE}" 2>&1; then
    record "- status: PASS"
  else
    record "- status: FAIL"
    record "- log: \`${LOG_FILE}\`"
    exit 1
  fi
  record ""
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

run_runtime_core_witness() {
  local api_host api_base
  local cookie_jar create_json
  local signup_out login_out
  local create_code stop_code route_code
  local session_id slug proxy_code
  local email="phase3-runtime-${RUN_ID}@medforge.test"

  api_host="$(remote_public_api_host "${DOMAIN}")"
  api_base="https://${api_host}"
  cookie_jar="$(mktemp /tmp/phase3-runtime-cookie.XXXXXX)"
  create_json="$(mktemp /tmp/phase3-runtime-create.XXXXXX)"
  signup_out="$(mktemp /tmp/phase3-runtime-signup.XXXXXX)"
  login_out="$(mktemp /tmp/phase3-runtime-login.XXXXXX)"

  signup_code="$(curl -sS -o "${signup_out}" -w '%{http_code}' \
    -c "${cookie_jar}" \
    -H 'content-type: application/json' \
    -X POST "${api_base}/api/v1/auth/signup" \
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
      -X POST "${api_base}/api/v1/auth/login" \
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
    -X POST "${api_base}/api/v1/sessions" \
    --data '{"tier":"public"}')"
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
      "https://$(remote_public_session_host "${slug}" "${DOMAIN}")" || echo 000)"
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
    -X POST "${api_base}/api/v1/sessions/${session_id}/stop")"
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
      "https://$(remote_public_session_host "${slug}" "${DOMAIN}")" || echo 000)"
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

  pytest -q \
    tests/test_api.py::test_session_create_private_returns_501 \
    tests/test_api.py::test_session_create_uppercase_tier_rejected \
    tests/test_api.py::test_session_create_requires_auth \
    tests/test_api.py::test_session_create_public_returns_running \
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
    echo "- public domain: \`${DOMAIN}\`"
    echo ""
  } >"${EVIDENCE_FILE}"

  run_check "Runtime Core Witness (Create/Stop/Snapshot)" "run_runtime_core_witness"
  run_check "Lifecycle and Recovery Test Lanes" "run_lifecycle_recovery_tests"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
