# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Is MedForge

MedForge is a single-host GPU-backed platform that provides code-server IDE sessions and medical-imaging competitions. The control plane (API, web, DB, reverse proxy) runs as Docker Compose services. The data plane is per-user Docker containers (`mf-session-<slug>`) each assigned one GPU, with ZFS-backed workspaces and stop-snapshots.

## Architecture Overview

```
Browser ──► Caddy (TLS, wildcard routing, forward-auth)
              ├─► medforge-web  (Next.js 16, standalone)
              ├─► medforge-api  (FastAPI, uvicorn)
              │     ├─► medforge-db  (MariaDB 11)
              │     ├─► Docker API   (session container lifecycle)
              │     └─► ZFS          (workspace provisioning, snapshots)
              ├─► medforge-api-worker  (async scoring worker)
              └─► mf-session-<slug>   (code-server per user, one GPU)
```

**Networks**: `medforge-control` (control plane), `medforge-external-sessions` (172.30.0.0/24, internet-allowed), `medforge-internal-sessions` (no egress). Caddy=172.30.0.2, API=172.30.0.3. East-west isolation: only Caddy can reach session `:8080`.

**Exposure model**: Routes split into EXTERNAL (`/api/v2/external/...`) and INTERNAL (`/api/v2/internal/...`). Internal session create requires `can_use_internal=true` on the user.

**Session lifecycle**: `STARTING → RUNNING → STOPPING → STOPPED` (or `ERROR`). Allocation locks the user row, selects a free GPU, generates an 8-char base32 slug, provisions a ZFS workspace, starts the container. Recovery thread polls active sessions and reconciles on startup.

**Competitions**: Permanent competitions with deterministic scoring. Submissions scored asynchronously by the worker. Leaderboard: best score per user, ties broken by earliest timestamp then smallest submission ID.

## API (`apps/api/`)

- **Framework**: FastAPI + SQLModel (MariaDB via PyMySQL/aiomysql) + Alembic migrations
- **Entry point**: `app/main.py` → mounts routers under `/api/v2/`, adds CORS and request-contract middleware, starts recovery thread
- **Routers**: `app/routers/auth.py` (register/login/logout), `app/routers/control_plane.py` (session CRUD), `app/routers/admin.py` (user/session admin), `app/routers/competitions/` (catalog, submissions, leaderboard, admin scoring)
- **Session runtime**: Ports & Adapters in `app/session_runtime/` — `ports.py` (protocols), `factory.py` (mock vs docker mode), `adapters/` (ZFS workspace, Docker container)
- **Scoring pipeline**: `app/scoring/` — `pipeline.py` orchestrates, `competition_specs.py` defines per-competition parsers/metrics, `manifest.py` validates evaluation contracts
- **Config**: `app/config.py` — frozen dataclass, all settings from env vars
- **DB models**: `app/models.py` (User, AuthSession, Pack, GpuDevice, SessionRecord, Dataset, Competition, Submission, SubmissionScore)
- **Python**: 3.12, `uv` for deps, venv at `apps/api/.venv`

## Web (`apps/web/`)

- **Framework**: Next.js 16 (App Router, React 19, TypeScript strict, Tailwind v4, shadcn/ui)
- **Route groups**: `(auth)/` (login/signup), `(marketing)/` (landing), `(app)/` (authenticated — dashboard, sessions, competitions, datasets, rankings, settings, admin)
- **Providers**: `components/providers/` — AuthProvider, SessionProvider, NotificationProvider, ThemeProvider
- **API client**: `lib/api.ts` + `lib/api-core.ts` — envelope-based (`{ data, meta }`), cookie auth, RFC 7807 errors
- **Surface detection**: `lib/surface.ts` (client) / `lib/server-surface.ts` (server) — determines external/internal from hostname
- **Type contracts**: `lib/contracts.ts` — all API response/request types
- **Path alias**: `@/*` maps to project root (e.g., `@/components/...`, `@/lib/...`)

## Development Commands

### API (run from `apps/api/`)
```bash
# Run all tests (exclude docker-dependent and load tests)
cd apps/api && python -m pytest -m "not docker and not load"

# Run a single test file
cd apps/api && python -m pytest tests/test_scoring.py

# Run a single test by name
cd apps/api && python -m pytest tests/test_scoring.py -k "test_name"

# Lint
cd apps/api && ruff check app/ tests/
cd apps/api && ruff format --check app/ tests/

# Auto-fix lint
cd apps/api && ruff check --fix app/ tests/
cd apps/api && ruff format app/ tests/

# Type check
cd apps/api && mypy app/

# DB migration (create)
cd apps/api && alembic revision --autogenerate -m "description"

# DB migration (apply)
cd apps/api && alembic upgrade head
```

### Web (run from `apps/web/`)
```bash
# Dev server (hot-reload)
cd apps/web && npm run dev

# Production build
cd apps/web && npm run build

# Lint
cd apps/web && npx eslint .

# E2E tests (requires running platform + Playwright installed)
cd apps/web && npm run test:e2e

# Install Playwright browsers
cd apps/web && npm run test:e2e:install

# E2E in headed mode (visible browser)
cd apps/web && npm run test:e2e:headed
```

### Docker Compose (from repo root)
```bash
# Bring up all services
docker compose -f deploy/compose/docker-compose.yml up -d

# Rebuild and restart API after code changes
docker compose -f deploy/compose/docker-compose.yml up -d --build medforge-api medforge-api-worker

# Rebuild and restart web
docker compose -f deploy/compose/docker-compose.yml up -d --build medforge-web

# View logs
docker compose -f deploy/compose/docker-compose.yml logs -f medforge-api
```

### Platform Validation (from repo root)
```bash
# Run all 6 validation phases sequentially
ops/host/validate-phases-all.sh

# Run a single phase
ops/host/validate-phase0-host.sh
ops/host/validate-phase2-auth-api.sh
# ... etc (phases 0-5)
```

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
- If canonical phase rows diverge between those two files, canonical status is invalid until reconciled.
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
- `docs/evidence/<date>/` stores run artifacts (`.md`, `.log`, and related outputs).
- Canonical evidence set is exactly the markdown files referenced by both `docs/phase-checking-strategy.md` and `docs/validation-logs.md`.
- If those pointer docs disagree for any phase row, canonical status is invalid until reconciled.
- `.log` artifacts may be retained as run history unless an explicit retention policy states otherwise.

## Engineering Standards
- Bash scripts use `set -euo pipefail`.
- Naming contracts: compose services/networks `medforge-*`; session containers `mf-session-<slug>`; session slug is 8-char lowercase base32 (see `apps/api/app/session_repo.py`).
- Import order: stdlib -> third-party -> local, with blank lines between groups (Python and TypeScript).
- Error handling: no graceful fallback masking; do not swallow errors with placeholder UI; show concrete failure messages.
- Code hygiene: delete dead code; do not comment it out; no wildcard imports (`from x import *`, `import *`); type hints on all Python function signatures; TypeScript `strict` mode; API responses use a consistent structured error shape (RFC 7807).
- Security/config: do not commit secrets (`deploy/compose/.env` for real values); hosts/ports/URLs from env/config (no hardcoded `localhost:8080`); keep `PACK_IMAGE` digest-pinned; preserve Caddy hardening `request_header -X-Upstream`; do not use `latest` Docker tags; prefer exact dependency pins and digest-pinned images; use `uv` over `pip`.
- Logging: include context identifiers (`session_id`, `user_id`, `slug`) in lifecycle logs.
- Testing: follow `docs/phase-checking-strategy.md` for canonical test lanes, runner commands, and evidence policy. Pytest markers: `docker` (needs real Docker), `load` (manual soak tests).

## Container Rebuild Policy
After editing source files for a containerized service, rebuild and restart the affected container(s) in the same change set. Do not consider a change complete until the running container reflects it.

| Source path | Affected service(s) | Command |
| --- | --- | --- |
| `apps/api/**` | `medforge-api`, `medforge-api-worker` | `docker compose -f deploy/compose/docker-compose.yml up -d --build medforge-api medforge-api-worker` |
| `apps/web/**` | `medforge-web` | `docker compose -f deploy/compose/docker-compose.yml up -d --build medforge-web` |
| `deploy/caddy/Caddyfile` | `medforge-caddy` | `docker compose -f deploy/compose/docker-compose.yml restart medforge-caddy` |
| `deploy/caddy/Dockerfile` | `medforge-caddy` | `docker compose -f deploy/compose/docker-compose.yml up -d --build medforge-caddy` |
| `deploy/compose/docker-compose.yml` | affected service(s) | `docker compose -f deploy/compose/docker-compose.yml up -d <service>` |

- `medforge-web-dev` (dev compose) uses a live volume mount — no rebuild needed for `apps/web/**` changes.
- Caddyfile is mounted read-only into the container — a restart (not rebuild) is sufficient for config changes.

## Runtime Contract Source Map
- Schema-level runtime contracts are code-owned by `apps/api/app/models.py`, `apps/api/app/schemas.py`, and `apps/api/alembic/versions/`.
