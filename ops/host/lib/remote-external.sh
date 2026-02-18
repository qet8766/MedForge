#!/usr/bin/env bash
#
# Shared helpers for remote-external validation checks.
# Canonical external hosts are derived from deploy/compose/.env DOMAIN:
#   web: external.<DOMAIN>
#   api: api.<DOMAIN>
#   wildcard probe: s-<slug>.external.<DOMAIN>

set -euo pipefail

remote_read_env_value() {
  local env_file="$1"
  local key="$2"
  if [ ! -f "${env_file}" ]; then
    return 0
  fi
  awk -F= -v k="${key}" '$1 == k {print substr($0, index($0, "=") + 1); exit}' "${env_file}"
}

remote_external_web_host() {
  local domain="$1"
  printf "external.%s\n" "${domain}"
}

remote_external_api_host() {
  local domain="$1"
  printf "api.%s\n" "${domain}"
}

remote_external_session_host() {
  local slug="$1"
  local domain="$2"
  printf "s-%s.external.%s\n" "${slug}" "${domain}"
}

remote_require_domain() {
  local domain="$1"
  if [ -z "${domain}" ]; then
    echo "ERROR: DOMAIN is required for remote-external validation."
    return 1
  fi
}

remote_require_cmds() {
  local cmd
  for cmd in "$@"; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
      echo "ERROR: required command not found: ${cmd}"
      return 1
    fi
  done
}

remote_dns_check_host() {
  local host="$1"
  dig +short "${host}" @1.1.1.1 | rg -q '.'
}

remote_dns_check_bundle() {
  local domain="$1"
  local wildcard_slug="${2:-phasecheck}"
  local web_host api_host wildcard_host

  web_host="$(remote_external_web_host "${domain}")"
  api_host="$(remote_external_api_host "${domain}")"
  wildcard_host="$(remote_external_session_host "${wildcard_slug}" "${domain}")"

  dig +short "${web_host}" @1.1.1.1
  dig +short "${api_host}" @1.1.1.1
  dig +short "${wildcard_host}" @1.1.1.1

  remote_dns_check_host "${web_host}"
  remote_dns_check_host "${api_host}"
  remote_dns_check_host "${wildcard_host}"
}

remote_tls_verify_host() {
  local host="$1"
  local out_file
  out_file="$(mktemp /tmp/remote-external-openssl.XXXXXX)"
  openssl s_client \
    -verify_return_error \
    -verify_hostname "${host}" \
    -connect "${host}:443" \
    </dev/null >"${out_file}" 2>&1
  rg -q "Verify return code: 0" "${out_file}"
  rm -f "${out_file}"
}

remote_health_check() {
  local domain="$1"
  local web_host api_host
  web_host="$(remote_external_web_host "${domain}")"
  api_host="$(remote_external_api_host "${domain}")"
  curl -fsS "https://${web_host}" >/dev/null
  curl -fsS "https://${api_host}/healthz" >/dev/null
}

# ---------------------------------------------------------------------------
# Shared assertion and JSON helpers (promoted from Phase 4)
# ---------------------------------------------------------------------------

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

assert_eq() {
  local got="$1"
  local expected="$2"
  local context="$3"
  if [ "${got}" != "${expected}" ]; then
    echo "ERROR: ${context}: expected '${expected}', got '${got}'"
    return 1
  fi
}

assert_body_contains() {
  local file="$1"
  local expr="$2"
  local context="$3"
  if ! python3 -c "
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data = json.load(f)
assert ${expr}
" "${file}" 2>/dev/null; then
    echo "ERROR: ${context}: body assertion failed (${expr})"
    return 1
  fi
}

cookie_token_from_jar() {
  local jar="$1"
  awk '$6 == "medforge_session" {print $7; exit}' "${jar}"
}

ensure_cookie_session() {
  local email="$1"
  local password="$2"
  local jar="$3"
  local label="$4"
  local api_base="${5:-${EXTERNAL_API_BASE_URL}}"
  local web_base="${6:-${EXTERNAL_WEB_BASE_URL}}"
  local signup_code login_code

  signup_code="$(curl -sS -o "/tmp/${PHASE_ID:-phase}-signup-${label}.out" -w '%{http_code}' \
    -X POST "${api_base}/api/v2/auth/signup" \
    -H 'content-type: application/json' \
    -H "Origin: ${web_base}" \
    -c "${jar}" -b "${jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")"

  if [ "${signup_code}" = "201" ]; then
    return
  fi

  if [ "${signup_code}" != "409" ]; then
    echo "ERROR: failed to sign up ${label} user (code=${signup_code})"
    cat "/tmp/${PHASE_ID:-phase}-signup-${label}.out" || true
    return 1
  fi

  login_code="$(curl -sS -o "/tmp/${PHASE_ID:-phase}-login-${label}.out" -w '%{http_code}' \
    -X POST "${api_base}/api/v2/auth/login" \
    -H 'content-type: application/json' \
    -H "Origin: ${web_base}" \
    -c "${jar}" -b "${jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")"

  if [ "${login_code}" != "200" ]; then
    echo "ERROR: failed to log in ${label} user (code=${login_code})"
    cat "/tmp/${PHASE_ID:-phase}-login-${label}.out" || true
    return 1
  fi
}
