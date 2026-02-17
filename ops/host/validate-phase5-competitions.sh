#!/usr/bin/env bash
#
# Phase 5 competition platform validation.
# Runs competition API and scoring lanes for contract fields, scoring, caps, and leaderboard rules.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT_DIR}/ops/host/lib/remote-external.sh"
source "${ROOT_DIR}/ops/host/lib/phase-runner.sh"
PHASE_ID="phase5-competitions"
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
Usage: bash ops/host/validate-phase5-competitions.sh

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

run_competition_api_tests() {
  cd "${ROOT_DIR}/apps/api"

  if [ ! -d ".venv" ]; then
    echo "ERROR: apps/api/.venv not found."
    return 1
  fi

  # shellcheck source=/dev/null
  . .venv/bin/activate

  run_pytest_with_optional_parallel \
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

run_dataset_isolation_contract_checks() {
  cd "${ROOT_DIR}"

  if rg -n "MEDFORGE_DATASETS_ROOT|COMPETITIONS_DATA_DIR" deploy/compose/.env.example deploy/compose/docker-compose.yml >/dev/null 2>&1; then
    echo "ERROR: legacy dataset env vars still present in deploy configuration."
    return 1
  fi

  rg -n "TRAINING_DATA_ROOT|PUBLIC_EVAL_DATA_ROOT|TEST_HOLDOUTS_DIR" \
    deploy/compose/.env.example \
    deploy/compose/docker-compose.yml \
    apps/api/app/config.py >/dev/null

  rg -n "volumes=\\{request\\.workspace_mount: \\{\"bind\": \"/workspace\", \"mode\": \"rw\"\\}\\}" \
    apps/api/app/session_runtime/adapters/docker_start.py >/dev/null

  if rg -n "TEST_HOLDOUTS_DIR|PUBLIC_EVAL_DATA_ROOT|test_holdouts_dir|public_eval_data_root|scoring-holdouts|public-eval" \
    apps/api/app/session_runtime >/dev/null 2>&1; then
    echo "ERROR: session runtime references scoring data roots."
    return 1
  fi
}

run_remote_competitions_smoke() {
  local api_base web_base
  local email cookie_jar signup_code login_code list_code detail_code leaderboard_code
  local list_json slug

  api_base="https://$(remote_external_api_host "${DOMAIN}")"
  web_base="https://$(remote_external_web_host "${DOMAIN}")"
  email="phase5-remote-${RUN_ID}@medforge.test"
  cookie_jar="$(mktemp /tmp/phase5-remote-cookie.XXXXXX)"
  list_json="$(mktemp /tmp/phase5-remote-list.XXXXXX)"

  signup_code="$(curl -sS -o /tmp/phase5-remote-signup.out -w '%{http_code}' \
    -X POST "${api_base}/api/v2/auth/signup" \
    -H 'content-type: application/json' \
    -H "Origin: ${web_base}" \
    -c "${cookie_jar}" -b "${cookie_jar}" \
    -d "{\"email\":\"${email}\",\"password\":\"Password123!\"}")"
  if [ "${signup_code}" = "409" ]; then
    login_code="$(curl -sS -o /tmp/phase5-remote-login.out -w '%{http_code}' \
      -X POST "${api_base}/api/v2/auth/login" \
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

  list_code="$(curl -sS -o "${list_json}" -w '%{http_code}' "${api_base}/api/v2/external/competitions")"
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

  detail_code="$(curl -sS -o /tmp/phase5-remote-detail.out -w '%{http_code}' "${api_base}/api/v2/external/competitions/${slug}")"
  if [ "${detail_code}" != "200" ]; then
    echo "ERROR: phase5 remote competition detail failed (code=${detail_code})"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  leaderboard_code="$(curl -sS -o /tmp/phase5-remote-leaderboard.out -w '%{http_code}' "${api_base}/api/v2/external/competitions/${slug}/leaderboard")"
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
  validate_parallel_env
  require_cmd curl
  require_cmd python3
  require_cmd rg

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 5 Competition Platform Evidence ($(date -u +%F))"
    echo ""
    echo "Generated by: \`ops/host/validate-phase5-competitions.sh\`"
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

  run_check_timed "Remote-External Competition Smoke" "run_remote_competitions_smoke"

  if [ "${VALIDATE_PARALLEL}" = "1" ]; then
    run_parallel_checks \
      "Dataset Isolation Policy Checks" "run_dataset_isolation_contract_checks" \
      "Competition API Contract Lanes" "run_competition_api_tests"
  else
    run_check_timed "Dataset Isolation Policy Checks" "run_dataset_isolation_contract_checks"
    run_check_timed "Competition API Contract Lanes" "run_competition_api_tests"
  fi

  run_check_timed "Competition Scoring Determinism Lanes" "run_scoring_tests"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
