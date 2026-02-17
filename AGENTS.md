# Repository Guidelines

## Policy Authority
- `AGENTS.md` is the top-level contributor and repository policy contract.
- Canonical runtime contracts live in `docs/`, with schema-level contracts owned by API code (see Runtime Contract Source Map).

## Runtime Truth and Validation

### Core Policy
- Canonical validation lane is `remote-public` only.
- API models include `PUBLIC` and `PRIVATE` tiers; runtime create for `tier=private` returns `501` (`NOT_IMPLEMENTED`).

### Runtime Claim Precedence
1. Latest accepted phase evidence in `docs/evidence/<date>/`
2. Validators in `ops/host/validate-phase*.sh` and `ops/host/validate-policy-remote-public.sh`
3. Source contracts in `apps/api`, `apps/web`, `deploy/caddy`, and `deploy/compose`

### Status Terms
- `VERIFIED`: backed by accepted canonical evidence.
- `UNVERIFIED`: described in code/docs but not covered by accepted evidence.
- `NOT_IMPLEMENTED`: intentionally modeled but blocked at runtime.

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
- `ops/host/lib/remote-public.sh`

## Documentation Governance

### Sync Rules
- Update docs in the same change set when implementation or plan behavior diverges.
- Keep `docs/phase-checking-strategy.md` and `docs/validation-logs.md` aligned with accepted runs.
- Each accepted phase run must produce `.md` and `.log` artifacts.
- Accepted evidence artifacts are immutable once committed.

### Docs Scope Ownership (Canonical)
This section defines explicit scope ownership for Markdown under `docs/`.

#### Governance
- Every retained top-level docs file must define:
  - `### Scope`
  - `### In Scope`
  - `### Out of Scope`
  - `### Canonical Sources`
- Runtime contract precedence remains:
  1. Latest accepted evidence under `docs/evidence/<date>/`
  2. Validation runners under `ops/host/validate-phase*.sh` and `ops/host/validate-policy-remote-public.sh`
  3. Source contracts in runtime code/config
- If a docs file cannot be assigned a narrow explicit scope, discard it.

#### Top-Level Scope Ownership
| File | Owner Scope | Keep/Discard |
| --- | --- | --- |
| `docs/architecture.md` | System-level runtime architecture, trust boundaries, status register | Keep |
| `docs/phase-checking-strategy.md` | Phase order, acceptance criteria, commands, evidence policy | Keep |
| `docs/validation-logs.md` | Concise canonical pointer index for latest accepted artifacts | Keep |
| `docs/sessions.md` | Session lifecycle/runtime/recovery contract | Keep |
| `docs/auth-routing.md` | Cookie auth, origin guard, wildcard routing/forward-auth contract | Keep |
| `docs/competitions.md` | Competition API/scoring/leaderboard contract | Keep |
| `docs/dataset-formats.md` | Dataset mirror layout and submission/holdout format contract | Keep |
| `docs/runbook.md` | Day-2 operations and troubleshooting procedures | Keep |

Schema-level enums/tables/invariants are code-owned by:
- `apps/api/app/models.py`
- `apps/api/app/schemas.py`
- `apps/api/app/migrations/`

#### Evidence Tree Policy (`docs/evidence/**`)
- Scope is directory-level, not per-artifact prose.
- `docs/evidence/<date>/` stores immutable run artifacts (`.md`, `.log`, and related outputs).
- Canonical evidence set is the files currently referenced by both:
  - `docs/phase-checking-strategy.md`
  - `docs/validation-logs.md`
- Markdown evidence files not referenced by those canonical pointers are discardable under aggressive cleanup.

Current canonical evidence markdown set:
- `docs/evidence/2026-02-17/phase0-host-20260217T064618Z.md`
- `docs/evidence/2026-02-17/phase1-bootstrap-20260217T064621Z.md`
- `docs/evidence/2026-02-17/phase2-auth-api-20260217T064639Z.md`
- `docs/evidence/2026-02-17/phase3-lifecycle-recovery-20260217T064705Z.md`
- `docs/evidence/2026-02-17/phase4-routing-e2e-20260217T064739Z.md`
- `docs/evidence/2026-02-17/phase5-competitions-20260217T064856Z.md`

#### Discard Criteria
Discard a docs artifact when any of the following is true:
- No explicit single owner scope can be defined.
- The file duplicates another canonical owner file and contributes no unique contract/ops content.
- For markdown artifacts under `docs/evidence/`: the artifact is not referenced by canonical phase/status pointers.

#### Scope Review Checklist
- All retained top-level docs have explicit scope sections.
- Each runtime topic has exactly one canonical owner (docs file or explicit code source).
- Canonical evidence pointers resolve to existing artifacts.
- Cross-links point from non-owner files to owner files rather than duplicating contracts.

## Project Structure and Module Organization
- `apps/web`: Next.js + TypeScript frontend.
- `apps/api`: FastAPI + SQLModel + Pydantic API and workers.
- `docs/`: architecture, sessions, routing/auth, competitions, dataset formats, phase strategy, validation logs, runbook, and evidence.
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

## Engineering Standards

### Coding Style and Naming Conventions
- Use 2-space indentation in YAML/Markdown.
- Bash scripts use `set -euo pipefail`.
- Keep env vars uppercase (for example `PACK_IMAGE`, `SESSION_SECRET`).
- Naming contracts:
  - Compose services/networks: `medforge-*`
  - Session containers: `mf-session-<slug>`
  - Session slug: 8-char lowercase base32 (see `apps/api/app/session_repo.py`)
- Import order: stdlib -> third-party -> local, with blank lines between groups (Python and TypeScript).
- Shell scripts should prefer named functions over long one-liner pipelines.

### Testing Guidelines
- Backend checks: `cd apps/api && pytest -q`
- Frontend checks: `cd apps/web && npm run build`
- Platform/session checks: follow `docs/phase-checking-strategy.md` with evidence (logs, curl output, screenshots).
- Ops script checks:
  - `find ops -name '*.sh' -print0 | xargs -0 -n1 bash -n`
  - `find ops -name '*.sh' -print0 | xargs -0 -n1 shellcheck` (when available)

### Commit and Pull Request Guidelines
- Use clear imperative commit messages.
- Include issue IDs in `MF-###` format when applicable (example: `MF-006 enforce race-safe GPU allocation`).
- PRs should include:
  - Scope summary and linked issue (`MF-###`)
  - Affected phase(s) and acceptance checks executed
  - Config/security impact (`.env`, networking, auth headers)
  - UI/routing screenshots when behavior changes

### Error Handling
- No graceful fallback masking. Do not swallow errors with placeholder UI.
- Let errors bubble up and show concrete failure messages.

### Code Hygiene
- File splitting: when a file exceeds ~150 lines, split it into focused files and add `@filename` references where code moved.
- TODO tracking: use `TODO(MF-###)` format.
- Dead code: delete it; do not comment it out.
- No wildcard imports (`from x import *`, `import *`).
- Type annotations: require hints on all Python function signatures and TypeScript `strict` mode.
- API responses: return structured error responses with a consistent shape, not raw strings.

### Security and Configuration
- Do not commit secrets; keep real values in `deploy/compose/.env`.
- Hosts, ports, and URLs must come from env/config; do not hardcode `localhost:8080`.
- Keep `PACK_IMAGE` digest-pinned.
- Preserve Caddy hardening: `request_header -X-Upstream`.
- Do not use `latest` Docker tags.
- For dependencies, prefer exact pins (or bounded ranges with lockfiles) and digest-pinned images.
- Always use `uv` over `pip` for Python package management.

### Logging
- Include context identifiers (`session_id`, `user_id`, `slug`) in lifecycle logs.

## Runtime Contract Source Map
Runtime behavior is documented in canonical docs under `docs/`:
- `docs/architecture.md`: cross-cutting runtime architecture, boundaries, and status register.
- `docs/sessions.md`: session create/stop/current behavior and recovery lifecycle.
- `docs/auth-routing.md`: cookie auth, origin policy, wildcard routing/auth contract.
- `docs/competitions.md`: competition API/scoring contract and leaderboard behavior.
- `docs/phase-checking-strategy.md` and `docs/validation-logs.md`: accepted phase evidence and canonical status.

Schema-level runtime contracts are code-owned:
- `apps/api/app/models.py`
- `apps/api/app/schemas.py`
- `apps/api/app/migrations/`

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
- `docs/phase-checking-strategy.md`
- `docs/validation-logs.md`
- `docs/runbook.md`
- `apps/api/app/models.py`
