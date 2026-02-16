#!/usr/bin/env bash
#
# Manual host validation runner for Gate 5/6 checks.
# Starts a local API process in docker runtime mode, performs create/stop and
# routing/isolation checks, and writes evidence to a markdown file.
#
# Usage:
#   bash infra/host/validate-gate56.sh
#   bash infra/host/validate-gate56.sh --with-browser
#
# Optional env:
#   API_PORT=8000
#   PACK_IMAGE=medforge-pack-default:local
#   EVIDENCE_FILE=docs/host-validation-$(date +%F).md
#   DB_PATH=apps/api/gate-evidence.db
#   BROWSER_DOMAIN=localtest.me
#   CADDY_PORT=18080
#   CADDY_IMAGE=caddy:2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d
#   WEB_PORT=3000
#   E2E_USER_EMAIL=e2e@example.com
#   E2E_USER_PASSWORD=Password123!

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_PORT="${API_PORT:-8000}"
API_URL="http://127.0.0.1:${API_PORT}"
REQUEST_API_URL="${API_URL}"
PACK_IMAGE="${PACK_IMAGE:-medforge-pack-default:local}"
PACK_IMAGE_RESOLVED=""
DB_PATH="${DB_PATH:-${ROOT_DIR}/apps/api/gate-evidence.db}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${ROOT_DIR}/docs/host-validation-$(date +%F).md}"
API_LOG="${ROOT_DIR}/apps/api/.gate56-api.log"

WITH_BROWSER=false
BROWSER_DOMAIN="${BROWSER_DOMAIN:-localtest.me}"
CADDY_PORT="${CADDY_PORT:-18080}"
WEB_PORT="${WEB_PORT:-3000}"
BROWSER_BASE_URL="${BROWSER_BASE_URL:-http://medforge.${BROWSER_DOMAIN}:${CADDY_PORT}}"
E2E_USER_EMAIL="${E2E_USER_EMAIL:-e2e-$(date +%s)@medforge.test}"
E2E_USER_PASSWORD="${E2E_USER_PASSWORD:-Password123!}"
E2E_RESULT_FILE="${E2E_RESULT_FILE:-/tmp/medforge-e2e-result.json}"
WEB_LOG="${ROOT_DIR}/apps/web/.gate56-web.log"
CADDY_LOG="${ROOT_DIR}/infra/host/.gate56-caddy.log"
CADDY_CONTAINER="medforge-gate56-caddy"
CADDY_IMAGE="${CADDY_IMAGE:-caddy:2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d}"
CADDYFILE=""
CADDY_STARTED=false

AUTH_USER_A_EMAIL="${AUTH_USER_A_EMAIL:-gate-user-a@medforge.test}"
AUTH_USER_B_EMAIL="${AUTH_USER_B_EMAIL:-gate-user-b@medforge.test}"
AUTH_USER_PASSWORD="${AUTH_USER_PASSWORD:-Password123!}"

API_PID=""
WEB_PID=""
SESSION_ID_A=""
SLUG_A=""
SESSION_ID_B=""
SLUG_B=""
COOKIE_JAR_A=""
COOKIE_JAR_B=""
AUTH_COOKIE_A=""
AUTH_COOKIE_B=""

usage() {
  cat <<'USAGE'
Usage: bash infra/host/validate-gate56.sh [--with-browser]

Options:
  --with-browser   Run Playwright browser smoke through a local Caddy wildcard proxy.
  -h, --help       Show this help message.
USAGE
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --with-browser)
        WITH_BROWSER=true
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
value = data.get(sys.argv[2], "")
print(value)
PY
}

cookie_token_from_jar() {
  local jar="$1"
  awk '$6 == "medforge_session" {print $7; exit}' "${jar}"
}

cleanup_stale_runtime() {
  pkill -f "uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT}" >/dev/null 2>&1 || true
  pkill -f "next dev --hostname 0.0.0.0 --port ${WEB_PORT}" >/dev/null 2>&1 || true
  docker rm -f "${CADDY_CONTAINER}" >/dev/null 2>&1 || true
}

resolve_pack_image() {
  if [[ "${PACK_IMAGE}" == *@sha256:* ]]; then
    PACK_IMAGE_RESOLVED="${PACK_IMAGE}"
    return
  fi

  local image_id
  image_id="$(docker image inspect --format '{{.Id}}' "${PACK_IMAGE}" 2>/dev/null || true)"
  if [ -z "${image_id}" ]; then
    echo "ERROR: PACK_IMAGE '${PACK_IMAGE}' is not digest-pinned and was not found locally."
    echo "Build the local pack first or pass PACK_IMAGE=<name>@sha256:<digest>."
    exit 1
  fi

  PACK_IMAGE_RESOLVED="${PACK_IMAGE}@${image_id}"
}

cleanup() {
  local exit_code=$?

  if [ -n "${SESSION_ID_A}" ]; then
    curl -sS -X POST "${REQUEST_API_URL}/api/v1/sessions/${SESSION_ID_A}/stop" -b "${COOKIE_JAR_A}" >/dev/null 2>&1 || true
  fi
  if [ -n "${SESSION_ID_B}" ]; then
    curl -sS -X POST "${REQUEST_API_URL}/api/v1/sessions/${SESSION_ID_B}/stop" -b "${COOKIE_JAR_B}" >/dev/null 2>&1 || true
  fi

  docker ps -a --format '{{.ID}} {{.Names}}' | awk '/ mf-session-/{print $1}' | xargs -r docker rm -f >/dev/null 2>&1 || true

  if docker ps -a --format '{{.Names}}' | rg -x "${CADDY_CONTAINER}" >/dev/null 2>&1; then
    docker rm -f "${CADDY_CONTAINER}" >/dev/null 2>&1 || true
  fi

  if [ -n "${WEB_PID}" ]; then
    kill "${WEB_PID}" >/dev/null 2>&1 || true
    wait "${WEB_PID}" >/dev/null 2>&1 || true
  fi

  if [ -n "${API_PID}" ]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" >/dev/null 2>&1 || true
  fi

  if [ -n "${CADDYFILE}" ] && [ -f "${CADDYFILE}" ]; then
    rm -f "${CADDYFILE}" || true
  fi

  if [ -n "${COOKIE_JAR_A}" ] && [ -f "${COOKIE_JAR_A}" ]; then
    rm -f "${COOKIE_JAR_A}" || true
  fi
  if [ -n "${COOKIE_JAR_B}" ] && [ -f "${COOKIE_JAR_B}" ]; then
    rm -f "${COOKIE_JAR_B}" || true
  fi

  exit "${exit_code}"
}
trap cleanup EXIT

wait_for_http() {
  local url="$1"
  local label="$2"
  for _ in $(seq 1 120); do
    if curl -sS "${url}" >/dev/null 2>&1; then
      return
    fi
    sleep 1
  done
  echo "ERROR: ${label} did not become ready at ${url}"
  exit 1
}

wait_for_api() {
  for _ in $(seq 1 120); do
    if curl -sS "${API_URL}/healthz" >/dev/null 2>&1; then
      return
    fi
    if [ -n "${API_PID}" ] && ! kill -0 "${API_PID}" >/dev/null 2>&1; then
      echo "ERROR: API exited before becoming healthy."
      tail -n 120 "${API_LOG}" || true
      exit 1
    fi
    sleep 1
  done
  echo "ERROR: API did not become ready at ${API_URL}/healthz"
  exit 1
}

ensure_cookie_session() {
  local email="$1"
  local password="$2"
  local jar="$3"
  local label="$4"

  local signup_code
  signup_code="$(curl -sS -o /tmp/g56_signup_"${label}".out -w '%{http_code}' \
    -X POST "${REQUEST_API_URL}/api/auth/signup" \
    -H 'content-type: application/json' \
    -H 'Origin: http://localhost:3000' \
    -c "${jar}" -b "${jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")"

  if [ "${signup_code}" = "201" ]; then
    return
  fi

  if [ "${signup_code}" != "409" ]; then
    echo "ERROR: failed to sign up ${label} user (code=${signup_code})"
    cat /tmp/g56_signup_"${label}".out || true
    exit 1
  fi

  local login_code
  login_code="$(curl -sS -o /tmp/g56_login_"${label}".out -w '%{http_code}' \
    -X POST "${REQUEST_API_URL}/api/auth/login" \
    -H 'content-type: application/json' \
    -H 'Origin: http://localhost:3000' \
    -c "${jar}" -b "${jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")"

  if [ "${login_code}" != "200" ]; then
    echo "ERROR: failed to log in ${label} user (code=${login_code})"
    cat /tmp/g56_login_"${label}".out || true
    exit 1
  fi
}

wait_for_session_proxy_not_running() {
  local host="$1"
  local cookie_token="$2"
  local timeout_seconds="${3:-90}"
  local code=""

  for _ in $(seq 1 "${timeout_seconds}"); do
    code="$(curl -sS -o /tmp/g5_stopped.out -w '%{http_code}' "${API_URL}/api/v1/auth/session-proxy" -H "Host: ${host}" -H "Cookie: medforge_session=${cookie_token}")"
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
  local timeout_seconds="${2:-90}"
  local snapshot=""

  for _ in $(seq 1 "${timeout_seconds}"); do
    snapshot="$(zfs list -t snapshot -H -o name | rg "tank/medforge/workspaces/.*/${session_id}@stop-" | tail -n1 || true)"
    if [ -n "${snapshot}" ]; then
      echo "${snapshot}"
      return 0
    fi
    sleep 1
  done

  echo "ERROR: timed out waiting for stop snapshot for session ${session_id}"
  return 1
}

start_local_api() {
  cd "${ROOT_DIR}/apps/api"
  if [ ! -d ".venv" ]; then
    echo "ERROR: apps/api/.venv not found. Create it first."
    exit 1
  fi

  rm -f "${DB_PATH}" "${API_LOG}"

  local cookie_domain=""
  if [ "${WITH_BROWSER}" = true ]; then
    cookie_domain=".medforge.${BROWSER_DOMAIN}"
  fi

  (
    # shellcheck source=/dev/null
    . .venv/bin/activate
    DATABASE_URL="sqlite:///${DB_PATH}" \
    DOMAIN="${BROWSER_DOMAIN}" \
    PACK_IMAGE="${PACK_IMAGE_RESOLVED}" \
    SESSION_RUNTIME_MODE=docker \
    SESSION_RUNTIME_USE_SUDO=true \
    PUBLIC_SESSIONS_NETWORK=medforge-public-sessions \
    WORKSPACE_ZFS_ROOT=tank/medforge/workspaces \
    SESSION_RECOVERY_ENABLED=true \
    SESSION_POLL_INTERVAL_SECONDS=5 \
    COOKIE_SECURE=false \
    COOKIE_DOMAIN="${cookie_domain}" \
    uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}" >"${API_LOG}" 2>&1
  ) &
  API_PID=$!
  wait_for_api
}

start_local_web() {
  cd "${ROOT_DIR}/apps/web"
  if [ ! -d node_modules ]; then
    npm install
  fi

  rm -f "${WEB_LOG}"

  (
    NEXT_PUBLIC_API_URL="${BROWSER_BASE_URL}" \
    NEXT_PUBLIC_DOMAIN="${BROWSER_DOMAIN}" \
    npm run dev -- --hostname 0.0.0.0 --port "${WEB_PORT}" >"${WEB_LOG}" 2>&1
  ) &
  WEB_PID=$!

  wait_for_http "http://127.0.0.1:${WEB_PORT}" "web app"
}

start_local_caddy() {
  if [ "${CADDY_STARTED}" = true ]; then
    return
  fi

  CADDYFILE="$(mktemp /tmp/medforge-gate56-caddy.XXXXXX)"
  cat >"${CADDYFILE}" <<CADDY
{
  auto_https off
}

http://medforge.${BROWSER_DOMAIN}:${CADDY_PORT} {
  @api path /api/*
  handle @api {
    reverse_proxy host.docker.internal:${API_PORT}
  }

  handle {
    reverse_proxy host.docker.internal:${WEB_PORT}
  }
}

http://api.medforge.${BROWSER_DOMAIN}:${CADDY_PORT} {
  reverse_proxy host.docker.internal:${API_PORT}
}

http://*.medforge.${BROWSER_DOMAIN}:${CADDY_PORT} {
  request_header -X-Upstream

  @session header_regexp session Host ^s-([a-z0-9]{8})\\.medforge\\.${BROWSER_DOMAIN}(:${CADDY_PORT})?$
  handle @session {
    forward_auth host.docker.internal:${API_PORT} {
      uri /api/v1/auth/session-proxy
      header_up Host {host}
      header_up X-Forwarded-For {remote}
      header_up Cookie {http.request.header.Cookie}
      header_up -Connection
      header_up -Upgrade
    }

    reverse_proxy mf-session-{re.session.1}:8080 {
      header_up Host {host}
      header_up X-Forwarded-Proto {scheme}
    }
  }

  handle {
    respond "Session host not matched" 404
  }
}
CADDY

  if docker ps -a --format '{{.Names}}' | rg -x "${CADDY_CONTAINER}" >/dev/null 2>&1; then
    docker rm -f "${CADDY_CONTAINER}" >/dev/null 2>&1
  fi

  rm -f "${CADDY_LOG}"
  docker run -d --rm \
    --name "${CADDY_CONTAINER}" \
    --network medforge-public-sessions \
    --add-host host.docker.internal:host-gateway \
    -p "${CADDY_PORT}:${CADDY_PORT}" \
    -v "${CADDYFILE}:/etc/caddy/Caddyfile:ro" \
    "${CADDY_IMAGE}" >/dev/null

  docker logs -f "${CADDY_CONTAINER}" >"${CADDY_LOG}" 2>&1 &
  wait_for_http "${BROWSER_BASE_URL}" "Caddy wildcard proxy"
  CADDY_STARTED=true
}

run_browser_smoke() {
  section "Gate 5/6 Browser + Websocket"

  require_cmd node
  require_cmd npm
  local api_log_lines_before=0
  if [ -f "${API_LOG}" ]; then
    api_log_lines_before="$(wc -l < "${API_LOG}")"
  fi

  start_local_web
  start_local_caddy

  cd "${ROOT_DIR}/apps/web"
  rm -f "${E2E_RESULT_FILE}"

  npm run test:e2e:install >/dev/null

  E2E_BASE_URL="${BROWSER_BASE_URL}" \
  E2E_DOMAIN="${BROWSER_DOMAIN}" \
  E2E_USER_EMAIL="${E2E_USER_EMAIL}" \
  E2E_USER_PASSWORD="${E2E_USER_PASSWORD}" \
  E2E_RESULT_FILE="${E2E_RESULT_FILE}" \
  E2E_IGNORE_HTTPS_ERRORS=true \
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

  local ws_auth_403=0
  if [ -f "${API_LOG}" ]; then
    ws_auth_403="$(tail -n +"$((api_log_lines_before + 1))" "${API_LOG}" | rg -c 'WebSocket /api/v1/auth/session-proxy.* 403' || true)"
  fi
  if ! [[ "${ws_auth_403}" =~ ^[0-9]+$ ]]; then
    ws_auth_403=0
  fi
  if [ "${ws_auth_403}" -gt 0 ]; then
    echo "ERROR: observed ${ws_auth_403} websocket auth 403 entries during browser validation."
    exit 1
  fi

  record "- browser base URL: \`${BROWSER_BASE_URL}\`"
  record "- e2e user: \`${E2E_USER_EMAIL}\`"
  record "- wildcard session URL: \`${session_url}\`"
  record "- wildcard slug: \`${slug}\`"
  record "- websocket attempts observed: \`${websocket_attempted}\`"
  record "- websocket connections with frame traffic: \`${websocket_with_frames}\`"
  record "- websocket auth 403 entries: \`${ws_auth_403}\`"
}

main() {
  parse_args "$@"
  if [ "${WITH_BROWSER}" = true ]; then
    REQUEST_API_URL="http://api.medforge.${BROWSER_DOMAIN}:${CADDY_PORT}"
  fi

  require_cmd curl
  require_cmd docker
  require_cmd python3
  require_cmd zfs
  require_cmd sudo
  require_cmd rg

  if ! sudo -n true >/dev/null 2>&1; then
    echo "ERROR: this script requires passwordless sudo (sudo -n)."
    exit 1
  fi

  if ! docker network inspect medforge-public-sessions >/dev/null 2>&1; then
    echo "ERROR: docker network 'medforge-public-sessions' not found."
    echo "Run: sudo bash infra/host/bootstrap-easy.sh"
    exit 1
  fi

  resolve_pack_image
  cleanup_stale_runtime

  {
    echo "## Host Validation Evidence ($(date +%F))"
    echo ""
    echo "Generated by: \`infra/host/validate-gate56.sh\`"
    echo ""
    echo "Runtime:"
    echo "- API URL: \`${API_URL}\`"
    echo "- Request API URL: \`${REQUEST_API_URL}\`"
    echo "- Pack image: \`${PACK_IMAGE_RESOLVED}\`"
    echo "- DB path: \`${DB_PATH}\`"
    echo "- Browser lane enabled: \`${WITH_BROWSER}\`"
    if [ "${WITH_BROWSER}" = true ]; then
      echo "- Browser base URL: \`${BROWSER_BASE_URL}\`"
      echo "- Browser domain: \`${BROWSER_DOMAIN}\`"
      echo "- Browser user: \`${E2E_USER_EMAIL}\`"
    fi
  } >"${EVIDENCE_FILE}"

  start_local_api
  if [ "${WITH_BROWSER}" = true ]; then
    start_local_caddy
    REQUEST_API_URL="http://api.medforge.${BROWSER_DOMAIN}:${CADDY_PORT}"
  fi
  COOKIE_JAR_A="$(mktemp /tmp/medforge-g56-cookie-a.XXXXXX)"
  COOKIE_JAR_B="$(mktemp /tmp/medforge-g56-cookie-b.XXXXXX)"
  ensure_cookie_session "${AUTH_USER_A_EMAIL}" "${AUTH_USER_PASSWORD}" "${COOKIE_JAR_A}" "user_a"
  ensure_cookie_session "${AUTH_USER_B_EMAIL}" "${AUTH_USER_PASSWORD}" "${COOKIE_JAR_B}" "user_b"
  AUTH_COOKIE_A="$(cookie_token_from_jar "${COOKIE_JAR_A}")"
  AUTH_COOKIE_B="$(cookie_token_from_jar "${COOKIE_JAR_B}")"
  if [ -z "${AUTH_COOKIE_A}" ] || [ -z "${AUTH_COOKIE_B}" ]; then
    echo "ERROR: failed to read medforge_session cookie from jar."
    exit 1
  fi

  section "Create Sessions"
  local resp_a resp_a_code
  resp_a_code="$(curl -sS -o /tmp/g6_create_a.out -w '%{http_code}' -X POST "${REQUEST_API_URL}/api/v1/sessions" -H 'content-type: application/json' -b "${COOKIE_JAR_A}" -d '{"tier":"public"}')"
  assert_eq "${resp_a_code}" "201" "create session A"
  resp_a="$(cat /tmp/g6_create_a.out)"
  record "- create A: \`${resp_a}\`"
  SESSION_ID_A="$(json_field "${resp_a}" "data['data']['session']['id']")"
  SLUG_A="$(json_field "${resp_a}" "data['data']['session']['slug']")"

  local resp_b resp_b_code
  resp_b_code="$(curl -sS -o /tmp/g6_create_b.out -w '%{http_code}' -X POST "${REQUEST_API_URL}/api/v1/sessions" -H 'content-type: application/json' -b "${COOKIE_JAR_B}" -d '{"tier":"public"}')"
  assert_eq "${resp_b_code}" "201" "create session B"
  resp_b="$(cat /tmp/g6_create_b.out)"
  record "- create B: \`${resp_b}\`"
  SESSION_ID_B="$(json_field "${resp_b}" "data['data']['session']['id']")"
  SLUG_B="$(json_field "${resp_b}" "data['data']['session']['slug']")"

  local host_a
  host_a="s-${SLUG_A}.medforge.${BROWSER_DOMAIN}"

  section "Gate 5 Auth Matrix"
  local code
  code="$(curl -sS -o /tmp/g5_unauth.out -w '%{http_code}' "${API_URL}/api/v1/auth/session-proxy" -H "Host: ${host_a}")"
  assert_eq "${code}" "401" "unauthenticated session-proxy"
  record "- unauthenticated: \`${code}\` body=\`$(cat /tmp/g5_unauth.out)\`"

  code="$(curl -sS -o /tmp/g5_nonowner.out -w '%{http_code}' "${API_URL}/api/v1/auth/session-proxy" -H "Host: ${host_a}" -H "Cookie: medforge_session=${AUTH_COOKIE_B}")"
  assert_eq "${code}" "403" "non-owner session-proxy"
  record "- non-owner: \`${code}\` body=\`$(cat /tmp/g5_nonowner.out)\`"

  local headers
  headers="$(curl -sS -D - -o /tmp/g5_owner.out "${API_URL}/api/v1/auth/session-proxy" -H "Host: ${host_a}" -H 'X-Upstream: evil-target:8080' -H "Cookie: medforge_session=${AUTH_COOKIE_A}")"
  code="$(printf '%s\n' "${headers}" | awk 'NR==1{print $2}')"
  assert_eq "${code}" "200" "owner session-proxy"
  local upstream
  upstream="$(printf '%s\n' "${headers}" | awk 'tolower($1)=="x-upstream:"{print $2}' | tr -d '\r')"
  if [ -z "${upstream}" ]; then
    echo "ERROR: missing X-Upstream response header"
    exit 1
  fi
  record "- owner spoof attempt: \`${code}\` x-upstream=\`${upstream}\`"

  section "Gate 5 Isolation"
  local firewall_out
  firewall_out="$(sudo bash "${ROOT_DIR}/infra/firewall/setup.sh")"
  record "- firewall: \`${firewall_out}\`"

  set +e
  docker exec "mf-session-${SLUG_B}" curl -sS --max-time 3 "http://mf-session-${SLUG_A}:8080" >/tmp/g5_iso.out 2>/tmp/g5_iso.err
  local iso_rc=$?
  set -e
  if [ "${iso_rc}" -eq 0 ]; then
    echo "ERROR: isolation check unexpectedly succeeded."
    echo "stdout: $(cat /tmp/g5_iso.out)"
    exit 1
  fi
  record "- session B -> session A :8080 blocked (exit=\`${iso_rc}\`, stderr=\`$(cat /tmp/g5_iso.err)\`)"

  section "Gate 6 End-to-End Core"
  local gpu_line
  gpu_line="$(docker exec "mf-session-${SLUG_A}" nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)"
  if [[ "${gpu_line}" != *NVIDIA* ]]; then
    echo "ERROR: unexpected GPU probe output: ${gpu_line}"
    exit 1
  fi
  record "- GPU in session A: \`${gpu_line}\`"

  local ws_line
  ws_line="$(docker exec "mf-session-${SLUG_A}" sh -lc 'echo alpha > /workspace/alpha.txt && cat /workspace/alpha.txt')"
  assert_eq "${ws_line}" "alpha" "workspace write/read"
  record "- workspace write/read: \`${ws_line}\`"

  local stop_a
  stop_a="$(curl -sS -X POST "${REQUEST_API_URL}/api/v1/sessions/${SESSION_ID_A}/stop" -b "${COOKIE_JAR_A}")"
  assert_eq "$(json_field "${stop_a}" "data['data']['message']")" "Session stop requested." "stop A message"
  record "- stop A: \`${stop_a}\`"

  code="$(wait_for_session_proxy_not_running "${host_a}" "${AUTH_COOKIE_A}")"
  record "- stopped host check: \`${code}\` body=\`$(cat /tmp/g5_stopped.out)\`"

  local snapshot
  snapshot="$(wait_for_stop_snapshot "${SESSION_ID_A}")"
  record "- snapshot: \`${snapshot}\`"

  local stop_b
  stop_b="$(curl -sS -X POST "${REQUEST_API_URL}/api/v1/sessions/${SESSION_ID_B}/stop" -b "${COOKIE_JAR_B}")"
  assert_eq "$(json_field "${stop_b}" "data['data']['message']")" "Session stop requested." "stop B message"
  wait_for_stop_snapshot "${SESSION_ID_B}" >/dev/null
  record "- stop B: \`${stop_b}\`"

  SESSION_ID_A=""
  SESSION_ID_B=""

  if [ "${WITH_BROWSER}" = true ]; then
    run_browser_smoke
  else
    section "Residual Gaps"
    record "- Caddy wildcard websocket validation is not covered by this script."
    record "- Full browser UI flow validation is not covered by this script."
  fi

  section "API Log Snippet"
  record '```text'
  tail -n 80 "${API_LOG}" | tee -a "${EVIDENCE_FILE}"
  record '```'

  if [ "${WITH_BROWSER}" = true ] && [ -f "${WEB_LOG}" ]; then
    section "Web Log Snippet"
    record '```text'
    tail -n 80 "${WEB_LOG}" | tee -a "${EVIDENCE_FILE}"
    record '```'
  fi

  if [ "${WITH_BROWSER}" = true ] && [ -f "${CADDY_LOG}" ]; then
    section "Caddy Log Snippet"
    record '```text'
    tail -n 80 "${CADDY_LOG}" | tee -a "${EVIDENCE_FILE}"
    record '```'
  fi

  echo ""
  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
