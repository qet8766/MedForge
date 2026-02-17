#!/usr/bin/env bash
#
# Shared helpers for remote-public validation checks.
# Canonical public hosts are derived from deploy/compose/.env DOMAIN:
#   web: medforge.<DOMAIN>
#   api: api.medforge.<DOMAIN>
#   wildcard probe: s-<slug>.medforge.<DOMAIN>

set -euo pipefail

remote_read_env_value() {
  local env_file="$1"
  local key="$2"
  if [ ! -f "${env_file}" ]; then
    return 0
  fi
  awk -F= -v k="${key}" '$1 == k {print substr($0, index($0, "=") + 1); exit}' "${env_file}"
}

remote_public_web_host() {
  local domain="$1"
  printf "medforge.%s\n" "${domain}"
}

remote_public_api_host() {
  local domain="$1"
  printf "api.medforge.%s\n" "${domain}"
}

remote_public_session_host() {
  local slug="$1"
  local domain="$2"
  printf "s-%s.medforge.%s\n" "${slug}" "${domain}"
}

remote_require_domain() {
  local domain="$1"
  if [ -z "${domain}" ]; then
    echo "ERROR: DOMAIN is required for remote-public validation."
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

  web_host="$(remote_public_web_host "${domain}")"
  api_host="$(remote_public_api_host "${domain}")"
  wildcard_host="$(remote_public_session_host "${wildcard_slug}" "${domain}")"

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
  out_file="$(mktemp /tmp/remote-public-openssl.XXXXXX)"
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
  web_host="$(remote_public_web_host "${domain}")"
  api_host="$(remote_public_api_host "${domain}")"
  curl -fsS "https://${web_host}" >/dev/null
  curl -fsS "https://${api_host}/healthz" >/dev/null
}
