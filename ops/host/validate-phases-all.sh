#!/usr/bin/env bash
#
# Sequential phase validator.
# Runs Phase 0 through Phase 5 and stops on first failure.
# Remote-public validation is mandatory; no local/browser mode flags.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

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
    echo "Remote-public validation is always enforced."
    usage
    exit 1
  fi
}

run_phase() {
  local label="$1"
  shift

  echo ""
  echo "==> Running ${label}"
  "$@"
}

main() {
  parse_args "$@"

  run_phase "Phase 0" bash "${ROOT_DIR}/ops/host/validate-phase0-host.sh"
  run_phase "Phase 1" bash "${ROOT_DIR}/ops/host/validate-phase1-bootstrap.sh"
  run_phase "Phase 2" bash "${ROOT_DIR}/ops/host/validate-phase2-auth-api.sh"
  run_phase "Phase 3" bash "${ROOT_DIR}/ops/host/validate-phase3-lifecycle-recovery.sh"
  run_phase "Phase 4" bash "${ROOT_DIR}/ops/host/validate-phase4-routing-e2e.sh"
  run_phase "Phase 5" bash "${ROOT_DIR}/ops/host/validate-phase5-competitions.sh"

  echo ""
  echo "All phases completed successfully."
}

main "$@"
