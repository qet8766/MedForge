# Repository Guidelines

## Source of Truth and Validation Policy
- `AGENTS.md` is the top-level contributor and repository policy contract.
- Canonical runtime contracts live in `docs/` (see Runtime Contract Source Map below).
- Validation lane is `remote-public` only.
- API models include `PUBLIC` and `PRIVATE` tiers; runtime create for `tier=private` returns `501` (`NOT_IMPLEMENTED`).
- Runtime claim precedence:
  1. Latest accepted phase evidence in `docs/evidence/<date>/`
  2. Validators in `ops/host/validate-phase*.sh` and `ops/host/validate-policy-remote-public.sh`
  3. Source contracts in `apps/api`, `apps/web`, `deploy/caddy`, and `deploy/compose`
- Status terms:
  - `VERIFIED`: backed by accepted canonical evidence.
  - `UNVERIFIED`: described in code/docs but not covered by accepted evidence.
  - `NOT_IMPLEMENTED`: intentionally modeled but blocked at runtime.
- Runtime claims become stale until revalidated when platform-affecting files change:
  - `apps/api/app/routers/*`
  - `apps/api/app/session_*`
  - `apps/api/app/deps.py`
  - `apps/api/app/config.py`
  - `deploy/caddy/Caddyfile`
  - `deploy/compose/docker-compose.yml`
  - `deploy/compose/.env` policy values
  - `ops/host/validate-phase*.sh`
  - `ops/host/lib/remote-public.sh`

## Project Structure and Module Organization
- `apps/web`: Next.js + TypeScript frontend.
- `apps/api`: FastAPI + SQLModel + Pydantic API and workers.
- `docs/`: architecture, sessions, routing/auth, data model, phase strategy, validation logs, runbook, and evidence.
- `deploy/compose/`: control-plane Compose stack and `.env.example`.
- `deploy/caddy/`: wildcard TLS/routing config.
- `deploy/packs/default/`: default code-server pack image.
- `ops/host/`: bootstrap, validation, and operations workflows.
- `ops/storage/` and `ops/network/`: ZFS and firewall host setup.
- `tools/data-prep/`: dataset prep and rehydration helpers.

## Build, Test, and Validation Commands
- `cp deploy/compose/.env.example deploy/compose/.env`
- `sudo bash ops/host/bootstrap-easy.sh`
- `bash ops/host/quick-check.sh`
- `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build`
- `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml logs -f medforge-api medforge-caddy`
- `cd apps/api && uv venv .venv && . .venv/bin/activate && uv pip install -e '.[dev,lint]'`
- `cd apps/api && pytest -q`
- `cd apps/web && npm install && npm run build`
- `POOL_DISKS='/dev/sdX' bash ops/storage/zfs-setup.sh`
- `bash ops/network/firewall-setup.sh`

Canonical remote-public validation:
- `bash ops/host/validate-policy-remote-public.sh`
- `bash ops/host/validate-phases-all.sh`

Phase-specific reruns:
- `bash ops/host/validate-phase0-host.sh`
- `bash ops/host/validate-phase1-bootstrap.sh`
- `bash ops/host/validate-phase2-auth-api.sh`
- `bash ops/host/validate-phase3-lifecycle-recovery.sh`
- `bash ops/host/validate-phase4-routing-e2e.sh`
- `bash ops/host/validate-phase5-competitions.sh`

## Coding Style and Naming Conventions
- Use 2-space indentation in YAML/Markdown.
- Bash scripts use `set -euo pipefail`.
- Keep env vars uppercase (for example `PACK_IMAGE`, `SESSION_SECRET`).
- Naming contracts:
  - Compose services/networks: `medforge-*`
  - Session containers: `mf-session-<slug>`
  - Session slug: 8-char lowercase base32 (see `docs/data-model.md`)
- Import order: stdlib -> third-party -> local, with blank lines between groups (Python and TypeScript).
- Shell scripts: prefer named functions over long one-liner pipelines.

## Testing Guidelines
- Backend checks: `cd apps/api && pytest -q`
- Frontend checks: `cd apps/web && npm run build`
- Platform/session checks: follow `docs/phase-checking-strategy.md` with evidence (logs, curl output, screenshots).
- Ops script checks:
  - `find ops -name '*.sh' -print0 | xargs -0 -n1 bash -n`
  - `find ops -name '*.sh' -print0 | xargs -0 -n1 shellcheck` (when available)

## Commit and Pull Request Guidelines
- Use clear imperative commit messages.
- Include issue IDs in `MF-###` format when applicable (example: `MF-006 enforce race-safe GPU allocation`).
- PRs should include:
  - Scope summary and linked issue (`MF-###`)
  - Affected phase(s) and acceptance checks executed
  - Config/security impact (`.env`, networking, auth headers)
  - UI/routing screenshots when behavior changes

## Error Handling
- No graceful fallback masking. Do not swallow errors with placeholder UI.
- Let errors bubble up and show concrete failure messages.

## Code Hygiene
- File splitting: when a file exceeds ~150 lines, split it into focused files and add `@filename` references where code moved.
- TODO tracking: use `TODO(MF-###)` format.
- Dead code: delete it; do not comment it out.
- No wildcard imports (`from x import *`, `import *`).
- Type annotations: require hints on all Python function signatures and TypeScript `strict` mode.
- API responses: return structured error responses with a consistent shape, not raw strings.

## Security and Configuration
- Do not commit secrets; keep real values in `deploy/compose/.env`.
- Hosts, ports, and URLs must come from env/config; no hardcoded `localhost:8080`.
- Keep `PACK_IMAGE` digest-pinned.
- Preserve Caddy hardening: `request_header -X-Upstream`.
- No `latest` Docker tags.
- For dependencies, prefer exact pins (or bounded ranges with lockfiles) and digest-pinned images.
- Always use `uv` over `pip` for Python package management.

## Logging
- Include context identifiers (`session_id`, `user_id`, `slug`) in lifecycle logs.

## Documentation Sync
- Update docs in the same change set when implementation or plan behavior diverges.
- Keep `docs/phase-checking-strategy.md` and `docs/validation-logs.md` aligned with accepted runs.
- Each accepted phase run must produce `.md` and `.log` artifacts.
- Accepted evidence artifacts are immutable once committed.

## Runtime Contract Source Map

Runtime behavior is documented in canonical docs under `docs/`:
- `docs/architecture.md`: cross-cutting runtime architecture, boundaries, and status register.
- `docs/sessions.md`: session create/stop/current behavior and recovery lifecycle.
- `docs/auth-routing.md`: cookie auth, origin policy, wildcard routing/auth contract.
- `docs/competitions.md`: competition API/scoring contract and leaderboard behavior.
- `docs/data-model.md`: schema-level entities and invariants.
- `docs/phase-checking-strategy.md` and `docs/validation-logs.md`: accepted phase evidence and canonical status.

Runtime summary:
- MedForge is a single-host control/data-plane platform for PUBLIC GPU code-server sessions and permanent PUBLIC competitions.
- API models include `PUBLIC` and `PRIVATE`, but runtime create for `tier=private` returns `501` (`NOT_IMPLEMENTED`).

Duplication policy:
- `AGENTS.md` is policy-oriented and pointer-oriented for runtime behavior.
- Runtime details should not be duplicated here when canonical docs above already define them.
- If duplicated claims diverge, canonical `docs/` runtime contract docs take precedence.

## Detailed References
- `docs/architecture.md`
- `docs/sessions.md`
- `docs/auth-routing.md`
- `docs/data-model.md`
- `docs/phase-checking-strategy.md`
- `docs/validation-logs.md`
- `docs/runbook.md`
