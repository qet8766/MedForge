# MedForge Phase Checking Strategy (Canonical)

This is the single source of truth for validation phase order, acceptance criteria, executable commands, and evidence policy.

### Scope

### In Scope

- canonical phase order and non-negotiable advancement rules
- per-phase acceptance criteria and runner commands
- evidence artifact policy and definition of done
- current canonical status pointers for each phase
- build/test/validation command entry points used by contributors and operators

### Out of Scope

- runtime architecture contract details (`docs/architecture.md`)
- endpoint-level domain contracts (`docs/sessions.md`, `docs/auth-routing.md`, `docs/competitions.md`)
- day-2 operational remediation playbooks (`docs/runbook.md`)

### Canonical Sources

- `ops/host/validate-policy-remote-external.sh`
- `ops/host/validate-phases-all.sh`
- `ops/host/validate-phase*.sh`
- `ops/host/bootstrap-easy.sh`
- `ops/host/quick-check.sh`
- `ops/storage/zfs-setup.sh`
- `ops/network/firewall-setup.sh`
- `deploy/compose/docker-compose.yml`
- `deploy/compose/.env.example`
- `docs/validation-logs.md`
- `docs/evidence/`

## Scope and Non-Negotiables

- Phase order is strict: `Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5`.
- Do not skip phases.
- Do not advance when the current phase is `FAIL` or `INCONCLUSIVE`.
- Runtime truth is required; tests are supporting evidence, not sufficient by themselves.
- Canonical validation is remote-external only. Localhost/local proxy modes are not accepted for `PASS`.
- Every accepted phase run must produce immutable timestamped evidence artifacts.
- All phases must validate response bodies (not just HTTP status codes) and record evidence detail.

## Status Vocabulary

- `PASS`: all required checks succeeded and required artifacts were produced.
- `FAIL`: one or more required checks failed.
- `INCONCLUSIVE`: checks were partial, interrupted, or evidence artifacts are missing.

## Current Canonical Status

> **STALE** -- Pre-rework evidence (2026-02-17) predates the phase restructure. Full revalidation required after rework merge.

| Phase | Name | Latest Evidence | Timestamp (UTC) | Status |
| --- | --- | --- | --- | --- |
| 0 | Host Infrastructure | `docs/evidence/2026-02-17/phase0-host-20260217T124352Z.md` | `2026-02-17T12:43:52Z` | STALE |
| 1 | Control Plane Bootstrap | `docs/evidence/2026-02-17/phase1-bootstrap-20260217T124354Z.md` | `2026-02-17T12:43:54Z` | STALE |
| 2 | Auth + API Contract Gate | `docs/evidence/2026-02-17/phase2-auth-api-20260217T124410Z.md` | `2026-02-17T12:44:10Z` | STALE |
| 3 | Session Lifecycle + E2E Runtime | `docs/evidence/2026-02-17/phase3-lifecycle-recovery-20260217T124425Z.md` | `2026-02-17T12:44:25Z` | STALE |
| 4 | Routing + Network Isolation | `docs/evidence/2026-02-17/phase4-routing-e2e-20260217T124444Z.md` | `2026-02-17T12:44:44Z` | STALE |
| 5 | Competition Platform + Browser | `docs/evidence/2026-02-17/phase5-competitions-20260217T124557Z.md` | `2026-02-17T12:45:57Z` | STALE |

## Evidence Policy

- Keep concise canonical pointers in `docs/validation-logs.md`.
- Store raw command transcripts and long evidence payloads under `docs/evidence/<date>/`.
- Treat evidence artifacts as immutable once written.
- Every phase `PASS` requires:
  - runner exit code `0`
  - markdown summary artifact with body-level validation detail
  - raw log artifact
  - concise index pointer update in `docs/validation-logs.md`

## Build, Test, and Validation Entry Points

Use this section as the canonical command inventory for local checks and remote-external validation progression.

### Environment and Platform Bring-Up

- `cp deploy/compose/.env.example deploy/compose/.env`
- `sudo bash ops/host/bootstrap-easy.sh`
- `bash ops/host/quick-check.sh`
- `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build`
- `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml logs -f medforge-api medforge-caddy`
- `POOL_DISKS='/dev/sdX' bash ops/storage/zfs-setup.sh`
- `bash ops/network/firewall-setup.sh`

### Backend, Frontend, and Script Checks

#### API (run from `apps/api/`)

Setup:
- `uv venv .venv && . .venv/bin/activate && uv pip install -e '.[dev,lint]'`

Tests:
- `python -m pytest -m "not docker and not load"` -- all tests (exclude docker-dependent and load)
- `python -m pytest tests/test_scoring.py` -- single file
- `python -m pytest tests/test_scoring.py -k "test_name"` -- single test by name
- `pytest -q` -- quick full run

Lint and format:
- `ruff check app/ tests/` -- lint check
- `ruff format --check app/ tests/` -- format check
- `ruff check --fix app/ tests/` -- auto-fix lint
- `ruff format app/ tests/` -- auto-fix format

Type check:
- `mypy app/`

DB migrations:
- `alembic revision --autogenerate -m "description"` -- create migration
- `alembic upgrade head` -- apply migrations

#### Web (run from `apps/web/`)

Setup and build:
- `npm install && npm run build` -- install deps and production build
- `npm run dev` -- dev server (hot-reload)

Lint:
- `npx eslint .`

E2E tests (requires running platform + Playwright installed):
- `npm run test:e2e` -- run E2E suite
- `npm run test:e2e:install` -- install Playwright browsers
- `npm run test:e2e:headed` -- E2E in headed mode (visible browser)

#### Shell scripts

- `find ops -name '*.sh' -print0 | xargs -0 -n1 bash -n`
- `find ops -name '*.sh' -print0 | xargs -0 -n1 shellcheck` (when available)

### Canonical Remote-External Validation

- `bash ops/host/validate-policy-remote-external.sh`
- `bash ops/host/validate-phases-all.sh`
- Platform/session checks must produce accepted phase evidence (`.md` and `.log` artifacts), with runtime witness output (logs, curl output, screenshots where required).
- Phase-specific reruns use the per-phase runner commands documented in each phase section below.

## Phase Acceptance Criteria and Commands

### Phase 0: Host Infrastructure

Purpose: verify host prerequisites for GPU sessions, storage, networks, and wildcard ingress.

Required checks:

- Host GPU visibility (`nvidia-smi -L`, `nvidia-smi`) with VRAM probe.
- GPU container runtime (`docker run --rm --gpus all ... nvidia-smi`).
- ZFS health and primitives (pool status, dataset list, write/read probe, snapshot create+restore probe).
- Docker network existence (`medforge-external-sessions`, `medforge-internal-sessions`).
- Wildcard DNS resolution for `medforge.<domain>`, `api.medforge.<domain>`, and `s-<slug>.medforge.<domain>`.
- Strict TLS validation (no insecure bypass).

Runner:

- `bash ops/host/validate-phase0-host.sh`

### Phase 1: Control Plane Bootstrap

Purpose: verify compose control plane, seed-state readiness, and runtime contract baselines.

Required checks:

- Compose services build and run successfully.
- Core services are running: `medforge-db`, `medforge-api`, `medforge-api-worker`, `medforge-web`, `medforge-caddy`.
- API `/healthz` body validation: JSON response with `status == "ok"`.
- Web root body validation: response contains expected HTML marker.
- DB migration alignment: alembic version table matches head revision.
- Seed invariants: `gpu_devices` rows `0..6` enabled and at least one digest-pinned pack row exists.
- Pytest lanes: `test_session_runtime_contract.py`, `test_session_runtime_resources.py`.

Runner:

- `bash ops/host/validate-phase1-bootstrap.sh`

### Phase 2: Auth + API Contract Gate

Purpose: verify cookie auth behavior, API contracts, protected-route denial paths, and config/log contracts.

Required checks:

- Signup/login/logout cookie flow with response body validation.
- Authenticated `/api/v2/me` behavior (body: email match) and unauthenticated denial behavior.
- Origin policy enforcement.
- Session-proxy owner/admin authorization and spoof-resistance behavior on API host.
- Auth rate-limit and token lifecycle checks.
- Admin pagination (cursor round-trip on `/admin/users`).
- Admin session listing (exposure filter).
- Session-by-ID fetch (owner, forbidden, missing).
- Config data isolation and log schema contract tests.

Runner:

- `bash ops/host/validate-phase2-auth-api.sh`

### Phase 3: Session Lifecycle + E2E Runtime

Purpose: verify EXTERNAL session lifecycle invariants, E2E runtime, and recovery correctness.

Required checks:

- EXTERNAL create/stop with response body validation (session id, slug, status fields).
- GPU probe inside session container (`nvidia-smi`).
- Workspace write/read verification inside session container.
- ZFS stop-snapshot verification after session stop.
- `/healthz` monitoring at pre-create, during-session, and post-stop checkpoints.
- INTERNAL create requires entitlement (`403` without `can_use_internal`, `201` with entitlement).
- GPU exclusivity and per-user concurrency limits under concurrency.
- Recovery transitions across `starting|running|stopping` and terminal states.
- Recovery health signaling (`/healthz` degradation and recovery behavior).
- Pytest lanes: `test_invariants.py`, session-by-ID tests.

Runner:

- `bash ops/host/validate-phase3-lifecycle-recovery.sh`

### Phase 4: Routing + Network Isolation

Purpose: verify wildcard routing authorization, east-west isolation, and network trust boundaries.

Required checks:

- Wildcard root routing authorization matrix (`401` unauthenticated, `403` non-owner, `200` owner) with body validation.
- Wildcard `/api/v2/auth/session-proxy` path is blocked (`403`) for external callers.
- Client-supplied `X-Upstream` spoof attempt has no routing effect when probing API-host session-proxy.
- East-west isolation blocks direct session-to-session `:8080` access.
- Pytest lanes: `test_isolation.py` (docker-marker tests: session-to-session HTTP/ICMP blocking).

Runner:

- `bash ops/host/validate-phase4-routing-isolation.sh`

### Phase 5: Competition Platform + Browser

Purpose: verify competition APIs, scoring pipeline, browser/websocket transport, and stuck scoring recovery.

Required checks:

- Competition catalog with body validation (items have `slug`, `title`, `status`).
- Competition detail with body validation (`rules`, `metric` fields).
- Leaderboard with body validation (`items` array).
- Valid submission scoring with non-null official primary score.
- Invalid submission and missing-resource error contract behavior.
- Daily cap enforcement.
- Deterministic leaderboard ranking and scoring determinism.
- Stuck scoring recovery test (worker requeues stalled submissions).
- Browser + websocket E2E lane (Playwright, always required).
- Dataset isolation policy checks.

Runner:

- `bash ops/host/validate-phase5-competitions.sh`

## Full Progression Runner

Run all phases in order:

- `bash ops/host/validate-policy-remote-external.sh`
- `bash ops/host/validate-phases-all.sh`

The progression runner must stop on first failure.

Optional performance controls (defaults shown):

- `VALIDATE_PARALLEL=1` enables safe in-phase parallel check groups in selected phases.
- `PYTEST_WORKERS=2` sets xdist worker count for accelerated pytest lanes.
- `PYTEST_DIST_MODE=loadscope` sets xdist distribution strategy for accelerated pytest lanes.
- `PHASE5_PLAYWRIGHT_INSTALL_MODE=auto` installs Playwright Chromium only when missing (`always` forces install each run).
- Set `VALIDATE_PARALLEL=0` to force sequential per-check execution.

## Definition of Done

- User can authenticate and create an EXTERNAL GPU session.
- GPU exclusivity and per-user limits are enforced under concurrent requests.
- Session work persists in unique per-session ZFS datasets.
- Stop finalization produces snapshot evidence.
- Recovery logic prevents stranded active sessions and reports health correctly.
- Routing and isolation enforce owner-bound access and block lateral `:8080` traffic.
- Competition flows score submissions with deterministic ranking and enforced daily caps.
- Browser + websocket transport verified end-to-end via Playwright.
- All phases validate response bodies and produce detailed evidence artifacts.
