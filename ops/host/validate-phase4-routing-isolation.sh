#!/usr/bin/env bash
#
# Phase 4 routing + network isolation validation.
# Verifies wildcard routing authorization, east-west isolation,
# and X-Upstream spoof resistance.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/ops/host/lib/remote-external.sh"
source "${ROOT_DIR}/ops/host/lib/phase-runner.sh"

PHASE_ID="phase4-routing-isolation"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/docs/evidence/$(date -u +%F)}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.md}"
LOG_FILE="${LOG_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.log}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/compose/.env}"

DOMAIN="${DOMAIN:-}"
AUTH_USER_A_EMAIL="${AUTH_USER_A_EMAIL:-phase-user-a@medforge.test}"
AUTH_USER_B_EMAIL="${AUTH_USER_B_EMAIL:-phase-user-b@medforge.test}"
AUTH_USER_PASSWORD="${AUTH_USER_PASSWORD:-Password123!}"
VALIDATE_PARALLEL="${VALIDATE_PARALLEL:-1}"
PYTEST_WORKERS="${PYTEST_WORKERS:-2}"
PYTEST_DIST_MODE="${PYTEST_DIST_MODE:-loadscope}"

PHASE_STATUS="INCONCLUSIVE"
EXTERNAL_WEB_HOST=""
EXTERNAL_API_HOST=""
EXTERNAL_WEB_BASE_URL=""
EXTERNAL_API_BASE_URL=""
SECTION_TIMER_STARTED_AT=0

SESSION_ID_A=""
SESSION_ID_B=""
SLUG_A=""
SLUG_B=""
COOKIE_JAR_A=""
COOKIE_JAR_B=""
AUTH_COOKIE_A=""
AUTH_COOKIE_B=""
CREATE_RESP_A=""
CREATE_RESP_B=""
CREATE_RESP_A_CODE=""
CREATE_RESP_B_CODE=""

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phase4-routing-isolation.sh

Phase 4 canonical validation is remote-external only; no mode flags are accepted.

Optional env:
  DOMAIN=<override>
  VALIDATE_PARALLEL=1
  PYTEST_WORKERS=2
  PYTEST_DIST_MODE=loadscope
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
  printf "%s\n" "${line}" | tee -a "${EVIDENCE_FILE}"
}

section() {
  local name="$1"
  printf "\n### %s\n\n" "${name}" | tee -a "${EVIDENCE_FILE}"
}

section_timing_begin() {
  SECTION_TIMER_STARTED_AT="$(date +%s)"
}

section_timing_end() {
  local ended_at elapsed
  ended_at="$(date +%s)"
  elapsed=$((ended_at - SECTION_TIMER_STARTED_AT))
  record "- duration_s: \`${elapsed}\`"
}

resolve_caddy_ip() {
  docker inspect -f '{{with index .NetworkSettings.Networks "medforge-external-sessions"}}{{.IPAddress}}{{end}}' medforge-caddy 2>/dev/null || true
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

ensure_cookie_sessions_parallel() {
  local rc_a rc_b
  local pid_a pid_b

  ensure_cookie_session "${AUTH_USER_A_EMAIL}" "${AUTH_USER_PASSWORD}" "${COOKIE_JAR_A}" "user_a" "${EXTERNAL_API_BASE_URL}" "${EXTERNAL_WEB_BASE_URL}" &
  pid_a=$!
  ensure_cookie_session "${AUTH_USER_B_EMAIL}" "${AUTH_USER_PASSWORD}" "${COOKIE_JAR_B}" "user_b" "${EXTERNAL_API_BASE_URL}" "${EXTERNAL_WEB_BASE_URL}" &
  pid_b=$!

  set +e
  wait "${pid_a}"
  rc_a=$?
  wait "${pid_b}"
  rc_b=$?
  set -e

  if [ "${rc_a}" -ne 0 ] || [ "${rc_b}" -ne 0 ]; then
    echo "ERROR: auth bootstrap failed (user_a_rc=${rc_a}, user_b_rc=${rc_b})."
    return 1
  fi
}

create_session_request() {
  local cookie_jar="$1"
  local out_file="$2"

  curl -sS -o "${out_file}" -w '%{http_code}' \
    -X POST "${EXTERNAL_API_BASE_URL}/api/v2/external/sessions" \
    -H 'content-type: application/json' \
    -b "${cookie_jar}" \
    -d '{}'
}

create_sessions_parallel() {
  local out_a out_b code_a code_b
  local rc_a rc_b
  local pid_a pid_b

  out_a="$(mktemp /tmp/p4_create_a.XXXXXX)"
  out_b="$(mktemp /tmp/p4_create_b.XXXXXX)"
  code_a="$(mktemp /tmp/p4_create_a_code.XXXXXX)"
  code_b="$(mktemp /tmp/p4_create_b_code.XXXXXX)"

  create_session_request "${COOKIE_JAR_A}" "${out_a}" >"${code_a}" &
  pid_a=$!
  create_session_request "${COOKIE_JAR_B}" "${out_b}" >"${code_b}" &
  pid_b=$!

  set +e
  wait "${pid_a}"
  rc_a=$?
  wait "${pid_b}"
  rc_b=$?
  set -e

  if [ "${rc_a}" -ne 0 ] || [ "${rc_b}" -ne 0 ]; then
    echo "ERROR: session creation request failed (a_rc=${rc_a}, b_rc=${rc_b})."
    rm -f "${out_a}" "${out_b}" "${code_a}" "${code_b}"
    return 1
  fi

  CREATE_RESP_A_CODE="$(tr -d '\n' <"${code_a}")"
  CREATE_RESP_B_CODE="$(tr -d '\n' <"${code_b}")"
  CREATE_RESP_A="$(cat "${out_a}")"
  CREATE_RESP_B="$(cat "${out_b}")"

  rm -f "${out_a}" "${out_b}" "${code_a}" "${code_b}"
}

run_isolation_pytest_lanes() {
  cd "${ROOT_DIR}/apps/api"

  if [ ! -d ".venv" ]; then
    echo "ERROR: apps/api/.venv not found."
    return 1
  fi

  # shellcheck source=/dev/null
  . .venv/bin/activate

  run_pytest_with_optional_parallel tests/test_isolation.py
}

cleanup() {
  local exit_code=$?

  if [ -n "${SESSION_ID_A}" ] && [ -n "${COOKIE_JAR_A}" ] && [ -f "${COOKIE_JAR_A}" ]; then
    curl -sS -X POST "${EXTERNAL_API_BASE_URL}/api/v2/external/sessions/${SESSION_ID_A}/stop" -b "${COOKIE_JAR_A}" >/dev/null 2>&1 || true
  fi
  if [ -n "${SESSION_ID_B}" ] && [ -n "${COOKIE_JAR_B}" ] && [ -f "${COOKIE_JAR_B}" ]; then
    curl -sS -X POST "${EXTERNAL_API_BASE_URL}/api/v2/external/sessions/${SESSION_ID_B}/stop" -b "${COOKIE_JAR_B}" >/dev/null 2>&1 || true
  fi

  if [ -n "${SLUG_A}" ]; then
    docker rm -f "mf-session-${SLUG_A}" >/dev/null 2>&1 || true
  fi
  if [ -n "${SLUG_B}" ]; then
    docker rm -f "mf-session-${SLUG_B}" >/dev/null 2>&1 || true
  fi

  if [ -n "${COOKIE_JAR_A}" ] && [ -f "${COOKIE_JAR_A}" ]; then
    rm -f "${COOKIE_JAR_A}" || true
  fi
  if [ -n "${COOKIE_JAR_B}" ] && [ -f "${COOKIE_JAR_B}" ]; then
    rm -f "${COOKIE_JAR_B}" || true
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

main() {
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
  fi
  if [ "$#" -ne 0 ]; then
    echo "ERROR: mode flags were removed. Phase 4 is remote-external only."
    usage
    exit 1
  fi

  require_cmd curl
  require_cmd docker
  require_cmd python3
  require_cmd rg
  require_cmd sudo

  if ! sudo -n true >/dev/null 2>&1; then
    echo "ERROR: this script requires passwordless sudo (sudo -n)."
    exit 1
  fi
  if ! docker network inspect medforge-external-sessions >/dev/null 2>&1; then
    echo "ERROR: docker network 'medforge-external-sessions' not found."
    echo "Run: sudo bash ops/host/bootstrap-easy.sh"
    exit 1
  fi

  if [ -z "${DOMAIN}" ]; then
    DOMAIN="$(remote_read_env_value "${ENV_FILE}" DOMAIN)"
  fi
  remote_require_domain "${DOMAIN}"
  validate_parallel_env

  EXTERNAL_WEB_HOST="$(remote_external_web_host "${DOMAIN}")"
  EXTERNAL_API_HOST="$(remote_external_api_host "${DOMAIN}")"
  EXTERNAL_WEB_BASE_URL="https://${EXTERNAL_WEB_HOST}"
  EXTERNAL_API_BASE_URL="https://${EXTERNAL_API_HOST}"

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 4 Routing + Network Isolation Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase4-routing-isolation.sh\`"
    echo ""
    echo "Runtime:"
    echo "- phase id: \`${PHASE_ID}\`"
    echo "- run id: \`${RUN_ID}\`"
    echo "- external web URL: \`${EXTERNAL_WEB_BASE_URL}\`"
    echo "- external api URL: \`${EXTERNAL_API_BASE_URL}\`"
    echo ""
  } >"${EVIDENCE_FILE}"

  section "Auth Session Bootstrap"
  section_timing_begin
  COOKIE_JAR_A="$(mktemp /tmp/medforge-phase4-cookie-a.XXXXXX)"
  COOKIE_JAR_B="$(mktemp /tmp/medforge-phase4-cookie-b.XXXXXX)"
  ensure_cookie_sessions_parallel
  AUTH_COOKIE_A="$(cookie_token_from_jar "${COOKIE_JAR_A}")"
  AUTH_COOKIE_B="$(cookie_token_from_jar "${COOKIE_JAR_B}")"
  if [ -z "${AUTH_COOKIE_A}" ] || [ -z "${AUTH_COOKIE_B}" ]; then
    echo "ERROR: failed to read medforge_session cookie from jar."
    exit 1
  fi
  record "- auth bootstrap: PASS"
  section_timing_end

  section "Create Sessions"
  section_timing_begin
  create_sessions_parallel
  assert_eq "${CREATE_RESP_A_CODE}" "201" "create session A"
  resp_a="${CREATE_RESP_A}"
  record "- create A: \`${resp_a}\`"
  SESSION_ID_A="$(json_field "${resp_a}" "data['data']['session']['id']")"
  SLUG_A="$(json_field "${resp_a}" "data['data']['session']['slug']")"

  assert_eq "${CREATE_RESP_B_CODE}" "201" "create session B"
  resp_b="${CREATE_RESP_B}"
  record "- create B: \`${resp_b}\`"
  SESSION_ID_B="$(json_field "${resp_b}" "data['data']['session']['id']")"
  SLUG_B="$(json_field "${resp_b}" "data['data']['session']['slug']")"
  section_timing_end

  host_a="$(remote_external_session_host "${SLUG_A}" "${DOMAIN}")"
  session_url_a="https://${host_a}/"
  blocked_proxy_url_a="${session_url_a}api/v2/auth/session-proxy"

  section "Routing Authorization Matrix"
  section_timing_begin
  code="$(curl -sS -o /tmp/p4_root_unauth.out -w '%{http_code}' "${session_url_a}")"
  assert_eq "${code}" "401" "unauthenticated wildcard root"
  record "- unauthenticated wildcard root: \`${code}\` body=\`$(cat /tmp/p4_root_unauth.out)\`"

  code="$(curl -sS -o /tmp/p4_root_nonowner.out -w '%{http_code}' "${session_url_a}" -H "Cookie: medforge_session=${AUTH_COOKIE_B}")"
  assert_eq "${code}" "403" "non-owner wildcard root"
  record "- non-owner wildcard root: \`${code}\` body=\`$(cat /tmp/p4_root_nonowner.out)\`"

  code="$(curl -sS -L -o /tmp/p4_root_owner.out -w '%{http_code}' "${session_url_a}" -H "Cookie: medforge_session=${AUTH_COOKIE_A}")"
  assert_eq "${code}" "200" "owner wildcard root"
  record "- owner wildcard root: \`${code}\`"

  code="$(curl -sS -o /tmp/p4_blocked_unauth.out -w '%{http_code}' "${blocked_proxy_url_a}")"
  assert_eq "${code}" "403" "blocked wildcard session-proxy unauthenticated"
  record "- blocked wildcard internal path unauthenticated: \`${code}\` body=\`$(cat /tmp/p4_blocked_unauth.out)\`"

  code="$(curl -sS -o /tmp/p4_blocked_owner.out -w '%{http_code}' "${blocked_proxy_url_a}" -H "Cookie: medforge_session=${AUTH_COOKIE_A}")"
  assert_eq "${code}" "403" "blocked wildcard session-proxy owner"
  record "- blocked wildcard internal path owner: \`${code}\` body=\`$(cat /tmp/p4_blocked_owner.out)\`"

  headers="$(docker exec medforge-api curl -sS -D - -o /dev/null \
    "http://medforge-api:8000/api/v2/auth/session-proxy" \
    -H "Host: ${host_a}" \
    -H 'X-Upstream: evil-target:8080' \
    -H "Cookie: medforge_session=${AUTH_COOKIE_A}")"
  code="$(printf '%s\n' "${headers}" | awk 'NR==1{print $2}')"
  assert_eq "${code}" "200" "owner session-proxy api-host contract"
  upstream="$(printf '%s\n' "${headers}" | awk 'tolower($1)=="x-upstream:"{print $2}' | tr -d '\r')"
  if [ -z "${upstream}" ]; then
    echo "ERROR: missing X-Upstream response header"
    exit 1
  fi
  assert_eq "${upstream}" "mf-session-${SLUG_A}:8080" "owner session-proxy canonical upstream"
  record "- owner spoof attempt via api host: \`${code}\` x-upstream=\`${upstream}\`"
  section_timing_end

  section "East-West Isolation"
  section_timing_begin
  caddy_ip="$(resolve_caddy_ip)"
  if [ -z "${caddy_ip}" ]; then
    echo "ERROR: could not resolve Caddy IP on medforge-external-sessions."
    exit 1
  fi
  firewall_out="$(sudo CADDY_IP="${caddy_ip}" bash "${ROOT_DIR}/ops/network/firewall-setup.sh")"
  record "- firewall: \`${firewall_out}\`"
  set +e
  docker exec "mf-session-${SLUG_B}" curl -sS --max-time 3 "http://mf-session-${SLUG_A}:8080" >/tmp/p4_iso.out 2>/tmp/p4_iso.err
  iso_rc=$?
  set -e
  if [ "${iso_rc}" -eq 0 ]; then
    echo "ERROR: isolation check unexpectedly succeeded."
    echo "stdout: $(cat /tmp/p4_iso.out)"
    exit 1
  fi
  record "- session B -> session A :8080 blocked (exit=\`${iso_rc}\`, stderr=\`$(cat /tmp/p4_iso.err)\`)"
  section_timing_end

  # Stop sessions before cleanup
  curl -sS -X POST "${EXTERNAL_API_BASE_URL}/api/v2/external/sessions/${SESSION_ID_A}/stop" -b "${COOKIE_JAR_A}" >/dev/null || true
  curl -sS -X POST "${EXTERNAL_API_BASE_URL}/api/v2/external/sessions/${SESSION_ID_B}/stop" -b "${COOKIE_JAR_B}" >/dev/null || true
  SESSION_ID_A=""
  SESSION_ID_B=""

  run_check_timed "Isolation Pytest Lanes" "run_isolation_pytest_lanes"

  section "Compose Log Snippets"
  section_timing_begin
  record '```text'
  docker compose --env-file "${ENV_FILE}" -f "${ROOT_DIR}/deploy/compose/docker-compose.yml" logs --tail 60 medforge-api medforge-web medforge-caddy | tee -a "${EVIDENCE_FILE}" >>"${LOG_FILE}"
  record '```'
  section_timing_end

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
