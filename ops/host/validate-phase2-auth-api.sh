#!/usr/bin/env bash
#
# Phase 2 auth and session API contract validation.
# Runs targeted test lanes for cookie auth, origin checks, and session proxy rules.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${ROOT_DIR}/ops/host/lib/remote-public.sh"
PHASE_ID="phase2-auth-api"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/docs/evidence/$(date -u +%F)}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.md}"
LOG_FILE="${LOG_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.log}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/compose/.env}"
DOMAIN="${DOMAIN:-}"

PHASE_STATUS="INCONCLUSIVE"

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phase2-auth-api.sh

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

run_auth_contract_tests() {
  cd "${ROOT_DIR}/apps/api"

  if [ ! -d ".venv" ]; then
    echo "ERROR: apps/api/.venv not found."
    return 1
  fi

  # shellcheck source=/dev/null
  . .venv/bin/activate

  pytest -q \
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

  api_base="https://$(remote_public_api_host "${DOMAIN}")"
  web_base="https://$(remote_public_web_host "${DOMAIN}")"
  email="phase2-remote-${RUN_ID}@medforge.test"
  cookie_jar="$(mktemp /tmp/phase2-remote-cookie.XXXXXX)"

  signup_code="$(curl -sS -o /tmp/phase2-remote-signup.out -w '%{http_code}' \
    -X POST "${api_base}/api/v1/auth/signup" \
    -H 'content-type: application/json' \
    -H "Origin: ${web_base}" \
    -c "${cookie_jar}" -b "${cookie_jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"

  if [ "${signup_code}" = "409" ]; then
    login_code="$(curl -sS -o /tmp/phase2-remote-login.out -w '%{http_code}' \
      -X POST "${api_base}/api/v1/auth/login" \
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
    "${api_base}/api/v1/me")"
  if [ "${me_code}" != "200" ]; then
    echo "ERROR: phase2 remote /api/v1/me failed (code=${me_code})"
    rm -f "${cookie_jar}"
    return 1
  fi

  logout_code="$(curl -sS -o /tmp/phase2-remote-logout.out -w '%{http_code}' \
    -X POST "${api_base}/api/v1/auth/logout" \
    -H "Origin: ${web_base}" \
    -b "${cookie_jar}" -c "${cookie_jar}")"
  if [ "${logout_code}" != "200" ]; then
    echo "ERROR: phase2 remote logout failed (code=${logout_code})"
    rm -f "${cookie_jar}"
    return 1
  fi

  me_after_logout_code="$(curl -sS -o /tmp/phase2-remote-me2.out -w '%{http_code}' \
    -b "${cookie_jar}" \
    "${api_base}/api/v1/me")"
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

  require_cmd curl

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 2 Auth and Session API Contract Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase2-auth-api.sh\`"
    echo ""
    echo "Runtime:"
    echo "- run id: \`${RUN_ID}\`"
    echo "- public domain: \`${DOMAIN}\`"
    echo "- api tests path: \`apps/api/tests\`"
    echo ""
  } >"${EVIDENCE_FILE}"

  run_check "Remote-Public Auth Smoke" "run_remote_auth_smoke"
  run_check "Auth and Session Contract Tests" "run_auth_contract_tests"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
