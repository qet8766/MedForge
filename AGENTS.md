# Repository Guidelines

## Policy Authority
- `AGENTS.md` is the top-level contributor and repository policy contract.
- Canonical policy filename is uppercase `AGENTS.md`; do not create or maintain lowercase `agents.md`.
- Canonical runtime contracts live in `docs/`, with schema-level contracts owned by API code (see Runtime Contract Source Map).

## Runtime Truth and Validation

### Core Policy
- Canonical validation lane is `remote-external` only.
- API models include `EXTERNAL` and `INTERNAL` exposures; internal session create is allowed only for users with `can_use_internal=true`.

### Runtime Claim Precedence
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

### Sync Rules
- Update docs in the same change set when implementation or plan behavior diverges.
- Keep `docs/phase-checking-strategy.md` and `docs/validation-logs.md` aligned with accepted runs.
- Each accepted phase run must produce `.md` and `.log` artifacts.
- Accepted evidence artifacts are immutable once committed.
- If canonical phase rows diverge between `docs/phase-checking-strategy.md` and `docs/validation-logs.md`, canonical status is invalid until reconciled.

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
  2. Validation runners under `ops/host/validate-phase*.sh` and `ops/host/validate-policy-remote-external.sh`

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
- `apps/api/alembic/versions/`

#### Evidence Tree Policy (`docs/evidence/**`)
- Scope is directory-level, not per-artifact prose.
- `docs/evidence/<date>/` stores run artifacts (`.md`, `.log`, and related outputs).
- Accepted artifacts become immutable once canonically referenced.
- Canonical evidence set is exactly the markdown files referenced by both:
  - `docs/phase-checking-strategy.md`
  - `docs/validation-logs.md`
- If those two pointer docs disagree for any phase row, canonical status is invalid until reconciled.
- Markdown evidence files not referenced by both canonical pointer docs are non-canonical and discardable.
- `.log` artifacts may be retained as run history unless an explicit retention policy states otherwise.

#### Discard Criteria
Discard a docs artifact when any of the following is true:
- No explicit single owner scope can be defined.
- The file duplicates another canonical owner file and contributes no unique contract/ops content.
- For markdown artifacts under `docs/evidence/`: the artifact is not referenced by both canonical pointer docs (`docs/phase-checking-strategy.md` and `docs/validation-logs.md`).

#### Scope Review Checklist
- All retained top-level docs have explicit scope sections.
- Each runtime topic has exactly one canonical owner (docs file or explicit code source).
- Every phase row is identical across `docs/phase-checking-strategy.md` and `docs/validation-logs.md` (phase id, path, timestamp, status).
- Canonical evidence pointers resolve to existing `.md` artifacts on disk.
- `AGENTS.md` does not declare timestamped canonical evidence lists; canonical evidence authority remains the two pointer docs.
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
- Canonical command inventory for bring-up, local checks, and remote-external phase validation is owned by `docs/phase-checking-strategy.md`.
- Use `docs/phase-checking-strategy.md` for per-phase rerun entrypoints and evidence requirements.
- Use `docs/runbook.md` for day-2 operational remediation procedures.

## Engineering Standards

### Coding Style and Naming Conventions
- Bash scripts use `set -euo pipefail`.
- Naming contracts:
  - Compose services/networks: `medforge-*`
  - Session containers: `mf-session-<slug>`
  - Session slug: 8-char lowercase base32 (see `apps/api/app/session_repo.py`)
- Import order: stdlib -> third-party -> local, with blank lines between groups (Python and TypeScript).

### Testing Guidelines
- Follow `docs/phase-checking-strategy.md` for canonical test lanes, runner commands, and evidence policy.
- Treat phase evidence artifacts and runtime witness output as required for platform/session claim validity.


### Error Handling
- No graceful fallback masking. Do not swallow errors with placeholder UI. Make it show concrete failure messages.

### Code Hygiene
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
- `apps/api/alembic/versions/`

Runtime summary:
- MedForge is a single-host control/data-plane platform for EXTERNAL GPU code-server sessions and permanent EXTERNAL competitions.
- API models include `EXTERNAL` and `INTERNAL`; internal session create is runtime-enabled behind `can_use_internal`.
