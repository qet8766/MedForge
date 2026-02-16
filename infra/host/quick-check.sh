#!/usr/bin/env bash
#
# Fast local quality check without host runtime dependencies.
#
# Usage:
#   bash infra/host/quick-check.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "${ROOT_DIR}/apps/api"
if [ ! -d ".venv" ]; then
  echo "ERROR: apps/api/.venv not found. Create it first."
  echo "  cd apps/api && uv venv .venv && . .venv/bin/activate && uv pip install -e '.[dev]'"
  exit 1
fi

# shellcheck source=/dev/null
. .venv/bin/activate
ruff check .
mypy app
pytest -q

cd "${ROOT_DIR}/apps/web"
npm run build

echo "Quick check passed."
