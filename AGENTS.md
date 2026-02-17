# Repository Guidelines

## Policy Authority
- `AGENTS.md` is the top-level contributor and repository policy contract.
- Canonical policy filename is uppercase `AGENTS.md`; do not create or maintain lowercase `agents.md`.
- Canonical runtime contracts live in `docs/`; schema-level contracts are code-owned (see Runtime Contract Source Map).

## Runtime Validation Contract
### Core Policy
- Canonical validation lane is `remote-external` only.
- API models include `EXTERNAL` and `INTERNAL` exposures; internal session create is allowed only for users with `can_use_internal=true`.

### Runtime Claim Precedence (Canonical)
1. Latest accepted phase evidence in `docs/evidence/<date>/`
2. Validators in `ops/host/validate-phase*.sh` and `ops/host/validate-policy-remote-external.sh`
3. Source contracts in `apps/api`, `apps/web`, `deploy/caddy`, and `deploy/compose`

### Revalidation Triggers
Runtime claims are stale until revalidated when platform-affecting files change:
- `apps/api/app/routers/*`
- `apps/api/app/session_*`
- `apps/api/app/deps.py`
- `apps/api/app/config.py`
- `deploy/caddy/Caddyfile`
- `deploy/compose/docker-compose.yml`
- `deploy/compose/.env` policy values
- `ops/host/validate-phase*.sh`
- `ops/host/lib/remote-external.sh`

## Documentation Governance
### Sync and Canonical Status
- Update docs in the same change set when implementation or plan behavior diverges.
- Keep `docs/phase-checking-strategy.md` and `docs/validation-logs.md` aligned with accepted runs.
- If canonical phase rows diverge between `docs/phase-checking-strategy.md` and `docs/validation-logs.md`, canonical status is invalid until reconciled.
- Every retained top-level docs file must define `### Scope`, `### In Scope`, `### Out of Scope`, and `### Canonical Sources`.

### Canonical Top-Level Docs (Owner Scope)
| File | Owner Scope |
| --- | --- |
| `docs/architecture.md` | System-level runtime architecture, trust boundaries, status register |
| `docs/phase-checking-strategy.md` | Phase order, acceptance criteria, commands, evidence policy |
| `docs/validation-logs.md` | Canonical pointer index for latest accepted artifacts |
| `docs/sessions.md` | Session lifecycle/runtime/recovery contract |
| `docs/auth-routing.md` | Cookie auth, origin guard, wildcard routing/forward-auth contract |
| `docs/competitions.md` | Competition API/scoring/leaderboard contract |
| `docs/dataset-formats.md` | Dataset mirror layout and submission/holdout format contract |
| `docs/runbook.md` | Day-2 operations and troubleshooting procedures |

### Evidence and Discard Rules
- Scope of `docs/evidence/**` is directory-level, not per-artifact prose.
- `docs/evidence/<date>/` stores run artifacts (`.md`, `.log`, and related outputs).
- Canonical evidence set is exactly the markdown files referenced by both `docs/phase-checking-strategy.md` and `docs/validation-logs.md`.
- If those pointer docs disagree for any phase row, canonical status is invalid until reconciled.
- `.log` artifacts may be retained as run history unless an explicit retention policy states otherwise.
- Scope review checklist: all retained top-level docs have scope sections

## Project Structure and Module Organization
- Key directories: `apps/web`, `apps/api`, `docs/`, `deploy/compose/`, `deploy/caddy/`, `deploy/packs/default/`, `ops/host/`, `ops/storage/`, `ops/network/`, `tools/data-prep/`.

## Build, Test, and Validation Commands
- Canonical command inventory for bring-up, local checks, and remote-external validation is owned by `docs/phase-checking-strategy.md`.

## Engineering Standards
- Bash scripts use `set -euo pipefail`.
- Naming contracts: compose services/networks `medforge-*`; session containers `mf-session-<slug>`; session slug is 8-char lowercase base32 (see `apps/api/app/session_repo.py`).
- Import order: stdlib -> third-party -> local, with blank lines between groups (Python and TypeScript).
- Testing: follow `docs/phase-checking-strategy.md` for canonical test lanes, runner commands, and evidence policy.
- Error handling: no graceful fallback masking; do not swallow errors with placeholder UI; show concrete failure messages.
- Code hygiene: delete dead code; do not comment it out; no wildcard imports (`from x import *`, `import *`); type hints on all Python function signatures; TypeScript `strict` mode; API responses use a consistent structured error shape.
- Security/config: do not commit secrets (`deploy/compose/.env` for real values); hosts/ports/URLs from env/config (no hardcoded `localhost:8080`); keep `PACK_IMAGE` digest-pinned; preserve Caddy hardening `request_header -X-Upstream`; do not use `latest` Docker tags; prefer exact dependency pins (or bounded ranges with lockfiles) and digest-pinned images; use `uv` over `pip`.
- Logging: include context identifiers (`session_id`, `user_id`, `slug`) in lifecycle logs.

## Runtime Contract Source Map
- Schema-level runtime contracts are code-owned by `apps/api/app/models.py`, `apps/api/app/schemas.py`, and `apps/api/alembic/versions/`.

## Runtime Summary
- MedForge is a single-host control/data-plane platform for EXTERNAL GPU code-server sessions and permanent EXTERNAL competitions.
- API models include `EXTERNAL` and `INTERNAL`; internal session create is runtime-enabled behind `can_use_internal`.
