#!/usr/bin/env bash
#
# Phase 4 remote-external routing/isolation/e2e validation.
# Canonical checks always run against external DNS + TLS endpoints.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/ops/host/lib/remote-external.sh"

PHASE_ID="phase4-routing-e2e"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/docs/evidence/$(date -u +%F)}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.md}"
LOG_FILE="${LOG_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.log}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/compose/.env}"

DOMAIN="${DOMAIN:-}"
PACK_IMAGE="${PACK_IMAGE:-}"

AUTH_USER_A_EMAIL="${AUTH_USER_A_EMAIL:-phase-user-a@medforge.test}"
AUTH_USER_B_EMAIL="${AUTH_USER_B_EMAIL:-phase-user-b@medforge.test}"
AUTH_USER_PASSWORD="${AUTH_USER_PASSWORD:-Password123!}"
E2E_USER_EMAIL="${E2E_USER_EMAIL:-e2e-$(date +%s)@medforge.test}"
E2E_USER_PASSWORD="${E2E_USER_PASSWORD:-Password123!}"
E2E_RESULT_FILE="${E2E_RESULT_FILE:-/tmp/medforge-e2e-result.json}"
PHASE4_ENFORCE_STOP_B_SNAPSHOT="${PHASE4_ENFORCE_STOP_B_SNAPSHOT:-0}"
PHASE4_PLAYWRIGHT_INSTALL_MODE="${PHASE4_PLAYWRIGHT_INSTALL_MODE:-auto}"

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
STOP_A_ROUTE_CODE=""
STOP_A_SNAPSHOT=""

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phase4-routing-e2e.sh

Phase 4 canonical validation is remote-external only; no mode flags are accepted.

Optional env:
  PHASE4_ENFORCE_STOP_B_SNAPSHOT=0|1 (default: 0)
  PHASE4_PLAYWRIGHT_INSTALL_MODE=auto|always (default: auto)
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

assert_eq() {
  local got="$1"
  local expected="$2"
  local context="$3"
  if [ "${got}" != "${expected}" ]; then
    echo "ERROR: ${context}: expected '${expected}', got '${got}'"
    exit 1
  fi
}

json_field() {
  local payload="$1"
  local expr="$2"
  python3 -c "import json,sys; data=json.load(sys.stdin); print(${expr})" <<<"${payload}"
}

json_file_key() {
  local path="$1"
  local key="$2"
  python3 - "$path" "$key" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
print(data.get(sys.argv[2], ""))
PY
}

cookie_token_from_jar() {
  local jar="$1"
  awk '$6 == "medforge_session" {print $7; exit}' "${jar}"
}

resolve_caddy_ip() {
  docker inspect -f '{{with index .NetworkSettings.Networks "medforge-external-sessions"}}{{.IPAddress}}{{end}}' medforge-caddy 2>/dev/null || true
}

validate_phase4_env() {
  case "${PHASE4_ENFORCE_STOP_B_SNAPSHOT}" in
    0|1)
      ;;
    *)
      echo "ERROR: PHASE4_ENFORCE_STOP_B_SNAPSHOT must be 0 or 1."
      return 1
      ;;
  esac

  case "${PHASE4_PLAYWRIGHT_INSTALL_MODE}" in
    auto|always)
      ;;
    *)
      echo "ERROR: PHASE4_PLAYWRIGHT_INSTALL_MODE must be 'auto' or 'always'."
      return 1
      ;;
  esac
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

ensure_cookie_session() {
  local email="$1"
  local password="$2"
  local jar="$3"
  local label="$4"
  local signup_code
  local login_code

  signup_code="$(curl -sS -o /tmp/${PHASE_ID}-signup-"${label}".out -w '%{http_code}' \
    -X POST "${EXTERNAL_API_BASE_URL}/api/v2/auth/signup" \
    -H 'content-type: application/json' \
    -H "Origin: ${EXTERNAL_WEB_BASE_URL}" \
    -c "${jar}" -b "${jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")"

  if [ "${signup_code}" = "201" ]; then
    return
  fi

  if [ "${signup_code}" != "409" ]; then
    echo "ERROR: failed to sign up ${label} user (code=${signup_code})"
    cat /tmp/${PHASE_ID}-signup-"${label}".out || true
    return 1
  fi

  login_code="$(curl -sS -o /tmp/${PHASE_ID}-login-"${label}".out -w '%{http_code}' \
    -X POST "${EXTERNAL_API_BASE_URL}/api/v2/auth/login" \
    -H 'content-type: application/json' \
    -H "Origin: ${EXTERNAL_WEB_BASE_URL}" \
    -c "${jar}" -b "${jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")"

  if [ "${login_code}" != "200" ]; then
    echo "ERROR: failed to log in ${label} user (code=${login_code})"
    cat /tmp/${PHASE_ID}-login-"${label}".out || true
    return 1
  fi
}

ensure_cookie_sessions_parallel() {
  local rc_a rc_b
  local pid_a pid_b

  ensure_cookie_session "${AUTH_USER_A_EMAIL}" "${AUTH_USER_PASSWORD}" "${COOKIE_JAR_A}" "user_a" &
  pid_a=$!
  ensure_cookie_session "${AUTH_USER_B_EMAIL}" "${AUTH_USER_PASSWORD}" "${COOKIE_JAR_B}" "user_b" &
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

  out_a="$(mktemp /tmp/g6_create_a.XXXXXX)"
  out_b="$(mktemp /tmp/g6_create_b.XXXXXX)"
  code_a="$(mktemp /tmp/g6_create_a_code.XXXXXX)"
  code_b="$(mktemp /tmp/g6_create_b_code.XXXXXX)"

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

wait_for_stop_a_finalization_parallel() {
  local host="$1"
  local cookie_token="$2"
  local session_id="$3"
  local route_file snapshot_file
  local rc_route rc_snapshot
  local pid_route pid_snapshot

  route_file="$(mktemp /tmp/${PHASE_ID}-route.XXXXXX)"
  snapshot_file="$(mktemp /tmp/${PHASE_ID}-snapshot.XXXXXX)"

  wait_for_session_host_not_routing "${host}" "${cookie_token}" >"${route_file}" &
  pid_route=$!
  wait_for_stop_snapshot "${session_id}" >"${snapshot_file}" &
  pid_snapshot=$!

  set +e
  wait "${pid_route}"
  rc_route=$?
  wait "${pid_snapshot}"
  rc_snapshot=$?
  set -e

  if [ "${rc_route}" -ne 0 ] || [ "${rc_snapshot}" -ne 0 ]; then
    echo "ERROR: stop A finalization failed (host_wait_rc=${rc_route}, snapshot_wait_rc=${rc_snapshot})."
    rm -f "${route_file}" "${snapshot_file}"
    return 1
  fi

  STOP_A_ROUTE_CODE="$(cat "${route_file}")"
  STOP_A_SNAPSHOT="$(cat "${snapshot_file}")"
  rm -f "${route_file}" "${snapshot_file}"
}

resolve_playwright_browser_path() {
  local configured="${PLAYWRIGHT_BROWSERS_PATH:-}"

  if [ -z "${configured}" ]; then
    printf "%s/.cache/ms-playwright\n" "${HOME}"
    return
  fi

  if [ "${configured}" = "0" ]; then
    printf "%s/apps/web/node_modules/playwright-core/.local-browsers\n" "${ROOT_DIR}"
    return
  fi

  printf "%s\n" "${configured}"
}

playwright_chromium_installed() {
  local browser_path

  browser_path="$(resolve_playwright_browser_path)"
  compgen -G "${browser_path}/chromium-*" >/dev/null
}

ensure_playwright_browser_ready() {
  case "${PHASE4_PLAYWRIGHT_INSTALL_MODE}" in
    always)
      npm run test:e2e:install >/dev/null
      record "- playwright chromium install: executed (mode=\`${PHASE4_PLAYWRIGHT_INSTALL_MODE}\`)"
      ;;
    auto)
      if playwright_chromium_installed; then
        record "- playwright chromium install: skipped (mode=\`${PHASE4_PLAYWRIGHT_INSTALL_MODE}\`)"
      else
        npm run test:e2e:install >/dev/null
        record "- playwright chromium install: executed (mode=\`${PHASE4_PLAYWRIGHT_INSTALL_MODE}\`)"
      fi
      ;;
  esac
}

run_browser_smoke() {
  section "Browser + Websocket Lane"
  section_timing_begin

  cd "${ROOT_DIR}/apps/web"
  if [ ! -d node_modules ]; then
    npm install
  fi
  rm -f "${E2E_RESULT_FILE}"
  ensure_playwright_browser_ready

  E2E_BASE_URL="${EXTERNAL_WEB_BASE_URL}" \
  E2E_DOMAIN="${DOMAIN}" \
  E2E_USER_EMAIL="${E2E_USER_EMAIL}" \
  E2E_USER_PASSWORD="${E2E_USER_PASSWORD}" \
  E2E_RESULT_FILE="${E2E_RESULT_FILE}" \
  E2E_IGNORE_HTTPS_ERRORS=false \
  npm run test:e2e -- e2e/session-smoke.spec.ts --reporter=line

  if [ ! -f "${E2E_RESULT_FILE}" ]; then
    echo "ERROR: browser smoke passed but no result file was written: ${E2E_RESULT_FILE}"
    exit 1
  fi

  local session_url websocket_attempted websocket_with_frames slug
  session_url="$(json_file_key "${E2E_RESULT_FILE}" "session_url")"
  websocket_attempted="$(json_file_key "${E2E_RESULT_FILE}" "websocket_attempted")"
  websocket_with_frames="$(json_file_key "${E2E_RESULT_FILE}" "websocket_with_frames")"
  slug="$(json_file_key "${E2E_RESULT_FILE}" "slug")"

  if ! [[ "${websocket_attempted}" =~ ^[0-9]+$ ]] || [ "${websocket_attempted}" -lt 1 ]; then
    echo "ERROR: expected at least one websocket attempt, got '${websocket_attempted}'."
    exit 1
  fi
  if ! [[ "${websocket_with_frames}" =~ ^[0-9]+$ ]] || [ "${websocket_with_frames}" -lt 1 ]; then
    echo "ERROR: expected at least one websocket with frame traffic, got '${websocket_with_frames}'."
    exit 1
  fi

  record "- browser base URL: \`${EXTERNAL_WEB_BASE_URL}\`"
  record "- e2e user: \`${E2E_USER_EMAIL}\`"
  record "- wildcard session URL: \`${session_url}\`"
  record "- wildcard slug: \`${slug}\`"
  record "- websocket attempts observed: \`${websocket_attempted}\`"
  record "- websocket connections with frame traffic: \`${websocket_with_frames}\`"
  section_timing_end
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

  validate_phase4_env

  require_cmd curl
  require_cmd docker
  require_cmd npm
  require_cmd openssl
  require_cmd python3
  require_cmd rg
  require_cmd sudo
  require_cmd zfs
  remote_require_cmds dig

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
  if [ -z "${PACK_IMAGE}" ]; then
    PACK_IMAGE="$(remote_read_env_value "${ENV_FILE}" PACK_IMAGE)"
  fi
  remote_require_domain "${DOMAIN}"

  EXTERNAL_WEB_HOST="$(remote_external_web_host "${DOMAIN}")"
  EXTERNAL_API_HOST="$(remote_external_api_host "${DOMAIN}")"
  EXTERNAL_WEB_BASE_URL="https://${EXTERNAL_WEB_HOST}"
  EXTERNAL_API_BASE_URL="https://${EXTERNAL_API_HOST}"

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 4 Routing and End-to-End Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase4-routing-e2e.sh\`"
    echo ""
    echo "Runtime:"
    echo "- phase id: \`${PHASE_ID}\`"
    echo "- run id: \`${RUN_ID}\`"
    echo "- external web URL: \`${EXTERNAL_WEB_BASE_URL}\`"
    echo "- external api URL: \`${EXTERNAL_API_BASE_URL}\`"
    echo "- pack image: \`${PACK_IMAGE}\`"
    echo "- enforce stop B snapshot: \`${PHASE4_ENFORCE_STOP_B_SNAPSHOT}\`"
    echo "- playwright install mode: \`${PHASE4_PLAYWRIGHT_INSTALL_MODE}\`"
    echo ""
  } >"${EVIDENCE_FILE}"

  section "Remote-External Preflight"
  section_timing_begin
  dns_result="$(remote_dns_check_bundle "${DOMAIN}" "phase4check")"
  printf "%s\n" "${dns_result}" >>"${EVIDENCE_FILE}"
  {
    printf "%s\n" "${dns_result}"
    remote_tls_verify_host "${EXTERNAL_WEB_HOST}"
    remote_tls_verify_host "${EXTERNAL_API_HOST}"
    remote_health_check "${DOMAIN}"
  } >>"${LOG_FILE}" 2>&1
  record "- DNS + TLS + health preflight: PASS"
  section_timing_end

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
  code="$(curl -sS -o /tmp/g5_root_unauth.out -w '%{http_code}' "${session_url_a}")"
  assert_eq "${code}" "401" "unauthenticated wildcard root"
  record "- unauthenticated wildcard root: \`${code}\` body=\`$(cat /tmp/g5_root_unauth.out)\`"

  code="$(curl -sS -o /tmp/g5_root_nonowner.out -w '%{http_code}' "${session_url_a}" -H "Cookie: medforge_session=${AUTH_COOKIE_B}")"
  assert_eq "${code}" "403" "non-owner wildcard root"
  record "- non-owner wildcard root: \`${code}\` body=\`$(cat /tmp/g5_root_nonowner.out)\`"

  code="$(curl -sS -L -o /tmp/g5_root_owner.out -w '%{http_code}' "${session_url_a}" -H "Cookie: medforge_session=${AUTH_COOKIE_A}")"
  assert_eq "${code}" "200" "owner wildcard root"
  record "- owner wildcard root: \`${code}\`"

  code="$(curl -sS -o /tmp/g5_blocked_unauth.out -w '%{http_code}' "${blocked_proxy_url_a}")"
  assert_eq "${code}" "403" "blocked wildcard session-proxy unauthenticated"
  record "- blocked wildcard internal path unauthenticated: \`${code}\` body=\`$(cat /tmp/g5_blocked_unauth.out)\`"

  code="$(curl -sS -o /tmp/g5_blocked_owner.out -w '%{http_code}' "${blocked_proxy_url_a}" -H "Cookie: medforge_session=${AUTH_COOKIE_A}")"
  assert_eq "${code}" "403" "blocked wildcard session-proxy owner"
  record "- blocked wildcard internal path owner: \`${code}\` body=\`$(cat /tmp/g5_blocked_owner.out)\`"

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
  docker exec "mf-session-${SLUG_B}" curl -sS --max-time 3 "http://mf-session-${SLUG_A}:8080" >/tmp/g5_iso.out 2>/tmp/g5_iso.err
  iso_rc=$?
  set -e
  if [ "${iso_rc}" -eq 0 ]; then
    echo "ERROR: isolation check unexpectedly succeeded."
    echo "stdout: $(cat /tmp/g5_iso.out)"
    exit 1
  fi
  record "- session B -> session A :8080 blocked (exit=\`${iso_rc}\`, stderr=\`$(cat /tmp/g5_iso.err)\`)"
  section_timing_end

  section "End-to-End Core Runtime"
  section_timing_begin
  gpu_line="$(docker exec "mf-session-${SLUG_A}" nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)"
  if [[ "${gpu_line}" != *NVIDIA* ]]; then
    echo "ERROR: unexpected GPU probe output: ${gpu_line}"
    exit 1
  fi
  record "- GPU in session A: \`${gpu_line}\`"

  ws_line="$(docker exec "mf-session-${SLUG_A}" sh -lc 'echo alpha > /workspace/alpha.txt && cat /workspace/alpha.txt')"
  assert_eq "${ws_line}" "alpha" "workspace write/read"
  record "- workspace write/read: \`${ws_line}\`"

  stop_a="$(curl -sS -X POST "${EXTERNAL_API_BASE_URL}/api/v2/external/sessions/${SESSION_ID_A}/stop" -b "${COOKIE_JAR_A}")"
  assert_eq "$(json_field "${stop_a}" "data['data']['message']")" "Session stop requested." "stop A message"
  record "- stop A: \`${stop_a}\`"

  wait_for_stop_a_finalization_parallel "${host_a}" "${AUTH_COOKIE_A}" "${SESSION_ID_A}"
  record "- stopped host check: \`${STOP_A_ROUTE_CODE}\` body=\`$(cat /tmp/${PHASE_ID}-stopped.out)\`"
  record "- snapshot: \`${STOP_A_SNAPSHOT}\`"
  SESSION_ID_A=""

  stop_b="$(curl -sS -X POST "${EXTERNAL_API_BASE_URL}/api/v2/external/sessions/${SESSION_ID_B}/stop" -b "${COOKIE_JAR_B}")"
  assert_eq "$(json_field "${stop_b}" "data['data']['message']")" "Session stop requested." "stop B message"
  record "- stop B: \`${stop_b}\`"
  if [ "${PHASE4_ENFORCE_STOP_B_SNAPSHOT}" = "1" ]; then
    snapshot_b="$(wait_for_stop_snapshot "${SESSION_ID_B}")"
    record "- stop B snapshot: \`${snapshot_b}\`"
    SESSION_ID_B=""
  else
    record "- stop B snapshot wait: skipped (PHASE4_ENFORCE_STOP_B_SNAPSHOT=0)"
  fi
  section_timing_end

  run_browser_smoke
  SESSION_ID_B=""

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
