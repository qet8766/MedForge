#!/usr/bin/env bash
#
# Sequential phase validator.
# Runs Phase 0 through Phase 5 and stops on first failure.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WITH_BROWSER=false

usage() {
  cat <<'USAGE'
Usage: bash ops/host/validate-phases-all.sh [--with-browser]

Options:
  --with-browser   Enable browser/websocket lane for Phase 4.
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

  if [ "${WITH_BROWSER}" = true ]; then
    run_phase "Phase 4" bash "${ROOT_DIR}/ops/host/validate-phase4-routing-e2e.sh" --with-browser
  else
    run_phase "Phase 4" bash "${ROOT_DIR}/ops/host/validate-phase4-routing-e2e.sh"
  fi

  run_phase "Phase 5" bash "${ROOT_DIR}/ops/host/validate-phase5-competitions.sh"

  echo ""
  echo "All phases completed successfully."
}

main "$@"
