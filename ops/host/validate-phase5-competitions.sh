#!/usr/bin/env bash
#
# Phase 5 competition platform validation.
# Runs competition API and scoring lanes for contract fields, scoring, caps, and leaderboard rules.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/ops/host/lib/remote-public.sh"
PHASE_ID="phase5-competitions"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/docs/evidence/$(date -u +%F)}"
EVIDENCE_FILE="${EVIDENCE_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.md}"
LOG_FILE="${LOG_FILE:-${EVIDENCE_DIR}/${PHASE_ID}-${RUN_ID}.log}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy/compose/.env}"
DOMAIN="${DOMAIN:-}"

PHASE_STATUS="INCONCLUSIVE"

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phase5-competitions.sh

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

run_competition_api_tests() {
  cd "${ROOT_DIR}/apps/api"

  if [ ! -d ".venv" ]; then
    echo "ERROR: apps/api/.venv not found."
    return 1
  fi

  # shellcheck source=/dev/null
  . .venv/bin/activate

  pytest -q \
    tests/test_api.py::test_list_competitions \
    tests/test_api.py::test_competition_detail_status \
    tests/test_api.py::test_competition_detail_missing_returns_problem_404 \
    tests/test_api.py::test_dataset_missing_returns_problem_404 \
    tests/test_api.py::test_submit_and_score_titanic \
    tests/test_api.py::test_submit_and_score_rsna_detection \
    tests/test_api.py::test_submit_and_score_cifar100 \
    tests/test_api.py::test_submission_cap_enforced \
    tests/test_api.py::test_invalid_schema_rejected \
    tests/test_api.py::test_leaderboard_respects_higher_is_better_flag \
    tests/test_api.py::test_leaderboard_rejects_invalid_pagination \
    tests/test_api.py::test_list_my_submissions_returns_desc_created_order \
    tests/test_api.py::test_submission_internal_failure_returns_problem_500 \
    tests/test_api.py::test_submission_rejects_disallowed_origin \
    tests/test_api.py::test_admin_score_rejects_disallowed_origin \
    tests/test_api.py::test_admin_score_missing_submission_returns_problem_404 \
    tests/test_api.py::test_admin_score_requires_admin_role \
    tests/test_api.py::test_submission_upload_size_limit_returns_structured_422
}

run_scoring_tests() {
  cd "${ROOT_DIR}/apps/api"

  # shellcheck source=/dev/null
  . .venv/bin/activate

  pytest -q tests/test_scoring.py
}

run_remote_competitions_smoke() {
  local api_base web_base
  local email cookie_jar signup_code login_code list_code detail_code leaderboard_code
  local list_json slug

  api_base="https://$(remote_public_api_host "${DOMAIN}")"
  web_base="https://$(remote_public_web_host "${DOMAIN}")"
  email="phase5-remote-${RUN_ID}@medforge.test"
  cookie_jar="$(mktemp /tmp/phase5-remote-cookie.XXXXXX)"
  list_json="$(mktemp /tmp/phase5-remote-list.XXXXXX)"

  signup_code="$(curl -sS -o /tmp/phase5-remote-signup.out -w '%{http_code}' \
    -X POST "${api_base}/api/v1/auth/signup" \
    -H 'content-type: application/json' \
    -H "Origin: ${web_base}" \
    -c "${cookie_jar}" -b "${cookie_jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"
  if [ "${signup_code}" = "409" ]; then
    login_code="$(curl -sS -o /tmp/phase5-remote-login.out -w '%{http_code}' \
      -X POST "${api_base}/api/v1/auth/login" \
      -H 'content-type: application/json' \
      -H "Origin: ${web_base}" \
      -c "${cookie_jar}" -b "${cookie_jar}" \
      -d "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"
    if [ "${login_code}" != "200" ]; then
      echo "ERROR: phase5 remote login failed (code=${login_code})"
      rm -f "${cookie_jar}" "${list_json}"
      return 1
    fi
  elif [ "${signup_code}" != "201" ]; then
    echo "ERROR: phase5 remote signup failed (code=${signup_code})"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  list_code="$(curl -sS -o "${list_json}" -w '%{http_code}' "${api_base}/api/v1/competitions")"
  if [ "${list_code}" != "200" ]; then
    echo "ERROR: phase5 remote competitions list failed (code=${list_code})"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  slug="$(python3 - <<'PY' "${list_json}"
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    payload = json.load(f)
data = payload.get("data", [])
if isinstance(data, list):
    rows = data
elif isinstance(data, dict):
    rows = data.get("items", [])
else:
    rows = []
print(rows[0]["slug"] if rows else "")
PY
)"
  if [ -z "${slug}" ]; then
    echo "ERROR: phase5 remote competitions list returned no items"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  detail_code="$(curl -sS -o /tmp/phase5-remote-detail.out -w '%{http_code}' "${api_base}/api/v1/competitions/${slug}")"
  if [ "${detail_code}" != "200" ]; then
    echo "ERROR: phase5 remote competition detail failed (code=${detail_code})"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  leaderboard_code="$(curl -sS -o /tmp/phase5-remote-leaderboard.out -w '%{http_code}' "${api_base}/api/v1/competitions/${slug}/leaderboard")"
  if [ "${leaderboard_code}" != "200" ]; then
    echo "ERROR: phase5 remote leaderboard failed (code=${leaderboard_code})"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  rm -f "${cookie_jar}" "${list_json}"
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
  require_cmd python3

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 5 Competition Platform Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase5-competitions.sh\`"
    echo ""
    echo "Runtime:"
    echo "- run id: \`${RUN_ID}\`"
    echo "- public domain: \`${DOMAIN}\`"
    echo ""
  } >"${EVIDENCE_FILE}"

  run_check "Remote-Public Competition Smoke" "run_remote_competitions_smoke"
  run_check "Competition API Contract Lanes" "run_competition_api_tests"
  run_check "Competition Scoring Determinism Lanes" "run_scoring_tests"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
