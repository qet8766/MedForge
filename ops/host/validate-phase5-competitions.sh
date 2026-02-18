#!/usr/bin/env bash
#
# Phase 5 competition platform + browser validation.
# Runs competition API, scoring, browser/websocket E2E, stuck scoring recovery,
# and dataset isolation lanes.

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

# Browser / Playwright settings (absorbed from Phase 4)
E2E_USER_EMAIL="${E2E_USER_EMAIL:-e2e-$(date +%s)@medforge.test}"
E2E_USER_PASSWORD="${E2E_USER_PASSWORD:-Password123!}"
E2E_RESULT_FILE="${E2E_RESULT_FILE:-/tmp/medforge-e2e-result.json}"
PHASE5_PLAYWRIGHT_INSTALL_MODE="${PHASE5_PLAYWRIGHT_INSTALL_MODE:-auto}"

PHASE_STATUS="INCONCLUSIVE"
EXTERNAL_WEB_HOST=""
EXTERNAL_API_HOST=""
EXTERNAL_WEB_BASE_URL=""
EXTERNAL_API_BASE_URL=""
SECTION_TIMER_STARTED_AT=0

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
  PHASE5_PLAYWRIGHT_INSTALL_MODE=auto|always (default: auto)
  E2E_USER_EMAIL=<override>
  E2E_USER_PASSWORD=<override>
  E2E_RESULT_FILE=/tmp/medforge-e2e-result.json
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

validate_playwright_env() {
  case "${PHASE5_PLAYWRIGHT_INSTALL_MODE}" in
    auto|always)
      ;;
    *)
      echo "ERROR: PHASE5_PLAYWRIGHT_INSTALL_MODE must be 'auto' or 'always'."
      exit 1
      ;;
  esac
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

# ---------------------------------------------------------------------------
# Playwright / Browser helpers (absorbed from Phase 4)
# ---------------------------------------------------------------------------

resolve_playwright_browser_path() {
  local configured=""
  configured="${PLAYWRIGHT_BROWSERS_PATH:-}"

  if [ -z "${configured}" ]; then
    printf "%s/apps/web/node_modules/playwright-core/.local-browsers\n" "${ROOT_DIR}"
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
  case "${PHASE5_PLAYWRIGHT_INSTALL_MODE}" in
    always)
      npm run test:e2e:install >/dev/null
      record "- playwright chromium install: executed (mode=\`${PHASE5_PLAYWRIGHT_INSTALL_MODE}\`)"
      ;;
    auto)
      if playwright_chromium_installed; then
        record "- playwright chromium install: skipped (mode=\`${PHASE5_PLAYWRIGHT_INSTALL_MODE}\`)"
      else
        npm run test:e2e:install >/dev/null
        record "- playwright chromium install: executed (mode=\`${PHASE5_PLAYWRIGHT_INSTALL_MODE}\`)"
      fi
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Competition API tests
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Scoring + stuck recovery tests
# ---------------------------------------------------------------------------

run_scoring_tests() {
  cd "${ROOT_DIR}/apps/api"

  # shellcheck source=/dev/null
  . .venv/bin/activate

  run_pytest_with_optional_parallel \
    tests/test_scoring.py \
    tests/test_scoring.py::test_worker_requeues_stuck_scoring_submissions
}

# ---------------------------------------------------------------------------
# Dataset isolation contract checks
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Remote competition smoke with body validation
# ---------------------------------------------------------------------------

run_remote_competitions_smoke() {
  local api_base web_base
  local email cookie_jar signup_code login_code list_code detail_code leaderboard_code
  local list_json slug

  api_base="${EXTERNAL_API_BASE_URL}"
  web_base="${EXTERNAL_WEB_BASE_URL}"
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

  # ---- Competition catalog with body validation ----
  list_code="$(curl -sS -o "${list_json}" -w '%{http_code}' "${api_base}/api/v2/external/competitions")"
  if [ "${list_code}" != "200" ]; then
    echo "ERROR: phase5 remote competitions list failed (code=${list_code})"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  # Body validation: verify catalog items have slug, title, status
  assert_body_contains "${list_json}" \
    "isinstance(data.get('data', []), list) and len(data['data']) > 0 and all(k in data['data'][0] for k in ('slug', 'title', 'status'))" \
    "competition catalog body"

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

  # ---- Competition detail with body validation ----
  detail_code="$(curl -sS -o /tmp/phase5-remote-detail.out -w '%{http_code}' "${api_base}/api/v2/external/competitions/${slug}")"
  if [ "${detail_code}" != "200" ]; then
    echo "ERROR: phase5 remote competition detail failed (code=${detail_code})"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  # Body validation: verify detail has rules and metric fields
  assert_body_contains /tmp/phase5-remote-detail.out \
    "'rules' in data.get('data', {}) and 'metric' in data.get('data', {})" \
    "competition detail body"

  # ---- Leaderboard with body validation ----
  leaderboard_code="$(curl -sS -o /tmp/phase5-remote-leaderboard.out -w '%{http_code}' "${api_base}/api/v2/external/competitions/${slug}/leaderboard")"
  if [ "${leaderboard_code}" != "200" ]; then
    echo "ERROR: phase5 remote leaderboard failed (code=${leaderboard_code})"
    rm -f "${cookie_jar}" "${list_json}"
    return 1
  fi

  # Body validation: verify leaderboard response has items array
  assert_body_contains /tmp/phase5-remote-leaderboard.out \
    "isinstance(data.get('data', {}).get('items', None), list)" \
    "leaderboard response body"

  echo "Remote competition smoke: catalog (${slug}), detail (rules+metric), leaderboard (items array) validated"
  rm -f "${cookie_jar}" "${list_json}"
}

# ---------------------------------------------------------------------------
# Browser + Websocket lane (absorbed from Phase 4)
# ---------------------------------------------------------------------------

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
    return 1
  fi

  local session_url websocket_attempted websocket_with_frames slug
  session_url="$(json_file_key "${E2E_RESULT_FILE}" "session_url")"
  websocket_attempted="$(json_file_key "${E2E_RESULT_FILE}" "websocket_attempted")"
  websocket_with_frames="$(json_file_key "${E2E_RESULT_FILE}" "websocket_with_frames")"
  slug="$(json_file_key "${E2E_RESULT_FILE}" "slug")"

  if ! [[ "${websocket_attempted}" =~ ^[0-9]+$ ]] || [ "${websocket_attempted}" -lt 1 ]; then
    echo "ERROR: expected at least one websocket attempt, got '${websocket_attempted}'."
    return 1
  fi
  if ! [[ "${websocket_with_frames}" =~ ^[0-9]+$ ]] || [ "${websocket_with_frames}" -lt 1 ]; then
    echo "ERROR: expected at least one websocket with frame traffic, got '${websocket_with_frames}'."
    return 1
  fi

  record "- browser base URL: \`${EXTERNAL_WEB_BASE_URL}\`"
  record "- e2e user: \`${E2E_USER_EMAIL}\`"
  record "- wildcard session URL: \`${session_url}\`"
  record "- wildcard slug: \`${slug}\`"
  record "- websocket attempts observed: \`${websocket_attempted}\`"
  record "- websocket connections with frame traffic: \`${websocket_with_frames}\`"
  section_timing_end
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

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
  validate_playwright_env

  EXTERNAL_WEB_HOST="$(remote_external_web_host "${DOMAIN}")"
  EXTERNAL_API_HOST="$(remote_external_api_host "${DOMAIN}")"
  EXTERNAL_WEB_BASE_URL="https://${EXTERNAL_WEB_HOST}"
  EXTERNAL_API_BASE_URL="https://${EXTERNAL_API_HOST}"

  require_cmd curl
  require_cmd npm
  require_cmd python3
  require_cmd rg

  mkdir -p "${EVIDENCE_DIR}"
  : >"${LOG_FILE}"

  {
    echo "## Phase 5 Competition Platform + Browser Evidence ($(date -u +%F))"
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
    echo "- playwright install mode: \`${PHASE5_PLAYWRIGHT_INSTALL_MODE}\`"
    echo ""
  } >"${EVIDENCE_FILE}"

  run_check_timed "Remote-External Competition Smoke (Body Validated)" "run_remote_competitions_smoke"

  if [ "${VALIDATE_PARALLEL}" = "1" ]; then
    run_parallel_checks \
      "Dataset Isolation Policy Checks" "run_dataset_isolation_contract_checks" \
      "Competition API Contract Lanes" "run_competition_api_tests"
  else
    run_check_timed "Dataset Isolation Policy Checks" "run_dataset_isolation_contract_checks"
    run_check_timed "Competition API Contract Lanes" "run_competition_api_tests"
  fi

  run_check_timed "Competition Scoring + Stuck Recovery Lanes" "run_scoring_tests"
  run_check_timed "Browser + Websocket E2E" "run_browser_smoke"

  PHASE_STATUS="PASS"
  record "## Verdict"
  record "- phase: \`${PHASE_ID}\`"
  record "- status: PASS"
  record "- log: \`${LOG_FILE}\`"

  echo "Validation complete: ${EVIDENCE_FILE}"
}

main "$@"
