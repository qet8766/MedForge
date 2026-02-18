#!/usr/bin/env bash
#
# Sequential phase validator.
# Runs Phase 0 through Phase 5 and stops on first failure.
# Remote-external validation is mandatory; no local/browser mode flags.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOTAL_STARTED_AT="$(date +%s)"
PHASE_TIMINGS=()

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phases-all.sh
USAGE
}

parse_args() {
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
  fi
  if [ "$#" -ne 0 ]; then
    echo "ERROR: validate-phases-all no longer accepts mode flags."
    echo "Remote-external validation is always enforced."
    usage
    exit 1
  fi
}

run_phase() {
  local label="$1"
  local started_at ended_at elapsed
  shift

  echo ""
  echo "==> Running ${label}"
  started_at="$(date +%s)"
  if "$@"; then
    ended_at="$(date +%s)"
    elapsed=$((ended_at - started_at))
    PHASE_TIMINGS+=("${label}:${elapsed}")
    echo "==> ${label} completed in ${elapsed}s"
  else
    ended_at="$(date +%s)"
    elapsed=$((ended_at - started_at))
    echo "==> ${label} failed after ${elapsed}s"
    return 1
  fi
}

main() {
  parse_args "$@"

  run_phase "Phase 0" bash "${ROOT_DIR}/ops/host/validate-phase0-host.sh"
  run_phase "Phase 1" bash "${ROOT_DIR}/ops/host/validate-phase1-bootstrap.sh"
  run_phase "Phase 2" bash "${ROOT_DIR}/ops/host/validate-phase2-auth-api.sh"
  run_phase "Phase 3" bash "${ROOT_DIR}/ops/host/validate-phase3-lifecycle-recovery.sh"
  run_phase "Phase 4" bash "${ROOT_DIR}/ops/host/validate-phase4-routing-isolation.sh"
  run_phase "Phase 5" bash "${ROOT_DIR}/ops/host/validate-phase5-competitions.sh"

  echo ""
  echo "Phase timing summary:"
  local timing label elapsed total_elapsed
  for timing in "${PHASE_TIMINGS[@]}"; do
    label="${timing%%:*}"
    elapsed="${timing##*:}"
    echo "- ${label}: ${elapsed}s"
  done
  total_elapsed=$(( $(date +%s) - TOTAL_STARTED_AT ))
  echo "- Total: ${total_elapsed}s"

  echo ""
  echo "All phases completed successfully."
}

main "$@"
