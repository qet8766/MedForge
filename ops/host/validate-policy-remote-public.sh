#!/usr/bin/env bash
#
# Repository policy guard for remote-public-only validation.
# Fails if tracked repo files reintroduce local/split-mode check logic.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

BANNED_PATTERNS=(
  "--with-browser"
  "--core-only"
  "localtest.me"
  "http://127.0.0.1"
  "http://localhost"
  "{\"localhost\", \"127.0.0.1\""
)

PATHSPECS=(
  "."
  ":(exclude)docs/evidence/**"
  ":(exclude)ops/host/validate-policy-remote-public.sh"
)

fail=0
for pattern in "${BANNED_PATTERNS[@]}"; do
  if git grep -n --fixed-strings -- "${pattern}" -- "${PATHSPECS[@]}" >/tmp/remote-policy-hit.out; then
    echo "ERROR: banned remote-public policy pattern found: ${pattern}"
    cat /tmp/remote-policy-hit.out
    fail=1
  fi
done

if [ "${fail}" -ne 0 ]; then
  exit 1
fi

echo "Remote-public validation policy check passed."
