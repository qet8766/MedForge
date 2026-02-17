#!/usr/bin/env bash
#
# Phase 2 auth and session API contract validation.
# Runs targeted test lanes for cookie auth, origin checks, and session proxy rules.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${ROOT_DIR}/ops/host/lib/remote-external.sh"
source "${ROOT_DIR}/ops/host/lib/phase-runner.sh"
PHASE_ID="phase2-auth-api"
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
Usage: bash ops/host/validate-phase2-auth-api.sh

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

run_auth_contract_tests() {
  cd "${ROOT_DIR}/apps/api"

  if [ ! -d ".venv" ]; then
    echo "ERROR: apps/api/.venv not found."
    return 1
  fi

  # shellcheck source=/dev/null
  . .venv/bin/activate

  run_pytest_with_optional_parallel \
    tests/test_api.py::test_signup_login_logout_cookie_flow \
    tests/test_api.py::test_me_requires_auth \
    tests/test_api.py::test_session_proxy_requires_auth \
    tests/test_api.py::test_session_proxy_returns_404_for_invalid_host \
    tests/test_api.py::test_session_proxy_enforces_owner_and_running \
    tests/test_auth_hardening.py::test_session_proxy_strips_spoofed_x_upstream \
    tests/test_auth_hardening.py::test_origin_matrix_allowed_origins \
    tests/test_auth_hardening.py::test_origin_matrix_rejected_origins \
    tests/test_auth_hardening.py::test_auth_signup_rate_limit_429 \
    tests/test_auth_hardening.py::test_auth_login_rate_limit_429 \
    tests/test_auth_hardening.py::test_logout_invalidates_token \
    tests/test_auth_hardening.py::test_idle_ttl_expires_session \
    tests/test_auth_hardening.py::test_max_ttl_expires_session \
    tests/test_control_plane.py::test_sessions_current_requires_auth \
    tests/test_control_plane.py::test_session_create_rejects_disallowed_origin \
    tests/test_control_plane.py::test_session_stop_rejects_disallowed_origin
}

run_remote_auth_smoke() {
  local api_base web_base
  local email cookie_jar signup_code login_code me_code logout_code me_after_logout_code
  local assert_code expected_code

  api_base="https://$(remote_external_api_host "${DOMAIN}")"
  web_base="https://$(remote_external_web_host "${DOMAIN}")"
  email="phase2-remote-${RUN_ID}@medforge.test"
  cookie_jar="$(mktemp /tmp/phase2-remote-cookie.XXXXXX)"

  signup_code="$(curl -sS -o /tmp/phase2-remote-signup.out -w '%{http_code}' \
    -X POST "${api_base}/api/v2/auth/signup" \
    -H 'content-type: application/json' \
    -H "Origin: ${web_base}" \
    -c "${cookie_jar}" -b "${cookie_jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"

  if [ "${signup_code}" = "409" ]; then
    login_code="$(curl -sS -o /tmp/phase2-remote-login.out -w '%{http_code}' \
      -X POST "${api_base}/api/v2/auth/login" \
      -H 'content-type: application/json' \
      -H "Origin: ${web_base}" \
      -c "${cookie_jar}" -b "${cookie_jar}" \
      -d "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"
    assert_code="${login_code}"
    expected_code="200"
  else
    assert_code="${signup_code}"
    expected_code="201"
  fi

  if [ "${assert_code}" != "${expected_code}" ]; then
    echo "ERROR: phase2 remote auth bootstrap failed (code=${assert_code}, expected=${expected_code})"
    rm -f "${cookie_jar}"
    return 1
  fi

  me_code="$(curl -sS -o /tmp/phase2-remote-me.out -w '%{http_code}' \
    -b "${cookie_jar}" \
    "${api_base}/api/v2/me")"
  if [ "${me_code}" != "200" ]; then
    echo "ERROR: phase2 remote /api/v2/me failed (code=${me_code})"
    rm -f "${cookie_jar}"
    return 1
  fi

  logout_code="$(curl -sS -o /tmp/phase2-remote-logout.out -w '%{http_code}' \
    -X POST "${api_base}/api/v2/auth/logout" \
    -H "Origin: ${web_base}" \
    -b "${cookie_jar}" -c "${cookie_jar}")"
  if [ "${logout_code}" != "200" ]; then
    echo "ERROR: phase2 remote logout failed (code=${logout_code})"
    rm -f "${cookie_jar}"
    return 1
  fi

  me_after_logout_code="$(curl -sS -o /tmp/phase2-remote-me2.out -w '%{http_code}' \
    -b "${cookie_jar}" \
    "${api_base}/api/v2/me")"
  if [ "${me_after_logout_code}" != "401" ]; then
    echo "ERROR: phase2 remote auth invalidation failed (code=${me_after_logout_code})"
    rm -f "${cookie_jar}"
    return 1
  fi

  rm -f "${cookie_jar}"
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

  require_cmd curl
  require_cmd python3

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 2 Auth and Session API Contract Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase2-auth-api.sh\`"
    echo ""
    echo "Runtime:"
    echo "- run id: \`${RUN_ID}\`"
    echo "- external domain: \`${DOMAIN}\`"
    echo "- api tests path: \`apps/api/tests\`"
    echo "- validate parallel: \`${VALIDATE_PARALLEL}\`"
    if [ "${VALIDATE_PARALLEL}" = "1" ]; then
      echo "- pytest workers: \`${PYTEST_WORKERS}\`"
      echo "- pytest dist mode: \`${PYTEST_DIST_MODE}\`"
    fi
    echo ""
  } >"${EVIDENCE_FILE}"

  if [ "${VALIDATE_PARALLEL}" = "1" ]; then
    run_parallel_checks \
      "Remote-External Auth Smoke" "run_remote_auth_smoke" \
      "Auth and Session Contract Tests" "run_auth_contract_tests"
  else
    run_check_timed "Remote-External Auth Smoke" "run_remote_auth_smoke"
    run_check_timed "Auth and Session Contract Tests" "run_auth_contract_tests"
  fi

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
