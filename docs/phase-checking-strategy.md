# MedForge Phase Checking Strategy (Canonical)

This is the single source of truth for validation phase order, acceptance criteria, executable commands, and evidence policy.

### Scope

### In Scope

- canonical phase order and non-negotiable advancement rules
- per-phase acceptance criteria and runner commands
- evidence artifact policy and definition of done
- current canonical status pointers for each phase

### Out of Scope

- runtime architecture contract details (`docs/architecture.md`)
- endpoint-level domain contracts (`docs/sessions.md`, `docs/auth-routing.md`, `docs/competitions.md`)
- day-2 operational remediation playbooks (`docs/runbook.md`)

### Canonical Sources

- `ops/host/validate-policy-remote-external.sh`
- `ops/host/validate-phases-all.sh`
- `ops/host/validate-phase*.sh`
- `docs/validation-logs.md`
- `docs/evidence/`

## Scope and Non-Negotiables

- Phase order is strict: `Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5`.
- Do not skip phases.
- Do not advance when the current phase is `FAIL` or `INCONCLUSIVE`.
- Runtime truth is required; tests are supporting evidence, not sufficient by themselves.
- Canonical validation is remote-external only. Localhost/local proxy modes are not accepted for `PASS`.
- Every accepted phase run must produce immutable timestamped evidence artifacts.

## Status Vocabulary

- `PASS`: all required checks succeeded and required artifacts were produced.
- `FAIL`: one or more required checks failed.
- `INCONCLUSIVE`: checks were partial, interrupted, or evidence artifacts are missing.

## Current Canonical Status (2026-02-17)

Latest full progression run completed under the remote-external-only phase model with all phases `PASS`.

| Phase | Name | Latest Evidence | Timestamp (UTC) | Status |
| --- | --- | --- | --- | --- |
| 0 | Host Foundation | `docs/evidence/2026-02-17/phase0-host-20260217T110808Z.md` | `2026-02-17T11:08:08Z` | PASS |
| 1 | Control Plane Bootstrap | `docs/evidence/2026-02-17/phase1-bootstrap-20260217T110811Z.md` | `2026-02-17T11:08:11Z` | PASS |
| 2 | Auth + Session API Contracts | `docs/evidence/2026-02-17/phase2-auth-api-20260217T110829Z.md` | `2026-02-17T11:08:29Z` | PASS |
| 3 | Session Lifecycle + Recovery | `docs/evidence/2026-02-17/phase3-lifecycle-recovery-20260217T110855Z.md` | `2026-02-17T11:08:55Z` | PASS |
| 4 | Routing, Isolation, End-to-End | `docs/evidence/2026-02-17/phase4-routing-e2e-20260217T110930Z.md` | `2026-02-17T11:09:30Z` | PASS |
| 5 | Competition Platform (Alpha) | `docs/evidence/2026-02-17/phase5-competitions-20260217T111048Z.md` | `2026-02-17T11:10:48Z` | PASS |

## Evidence Policy

- Keep concise canonical pointers in `docs/validation-logs.md`.
- Store raw command transcripts and long evidence payloads under `docs/evidence/<date>/`.
- Treat evidence artifacts as immutable once written.
- Every phase `PASS` requires:
  - runner exit code `0`
  - markdown summary artifact
  - raw log artifact
  - concise index pointer update in `docs/validation-logs.md`

## Phase Acceptance Criteria and Commands

### Phase 0: Host Foundation

Purpose: verify host prerequisites for GPU sessions and wildcard ingress.

Required checks:

- Host GPU visibility (`nvidia-smi -L`, `nvidia-smi`).
- GPU container runtime (`docker run --rm --gpus all ... nvidia-smi`).
- ZFS health and primitives (pool status, dataset list, write/read probe, snapshot probe).
- Wildcard DNS resolution for `medforge.<domain>`, `api.medforge.<domain>`, and `s-<slug>.medforge.<domain>`.
- Strict TLS validation (no insecure bypass).

Runner:

- `bash ops/host/validate-phase0-host.sh`

### Phase 1: Control Plane Bootstrap

Purpose: verify compose control plane and seed-state readiness.

Required checks:

- Compose services build and run successfully.
- Core services are running: `medforge-db`, `medforge-api`, `medforge-api-worker`, `medforge-web`, `medforge-caddy`.
- API and web are reachable from within their containers.
- Seed invariants: `gpu_devices` rows `0..6` enabled and at least one digest-pinned pack row exists.

Runner:

- `bash ops/host/validate-phase1-bootstrap.sh`

### Phase 2: Auth + Session API Contracts

Purpose: verify cookie auth behavior, protected-route denial paths, and internal session-proxy authorization contract.

Required checks:

- Signup/login/logout cookie flow.
- Authenticated `/api/v2/me` behavior and unauthenticated denial behavior.
- Origin policy enforcement.
- Session-proxy owner/admin authorization and spoof-resistance behavior on API host.
- Auth rate-limit and token lifecycle checks.

Runner:

- `bash ops/host/validate-phase2-auth-api.sh`

### Phase 3: Session Lifecycle + Recovery

Purpose: verify EXTERNAL session lifecycle invariants and recovery correctness.

Required checks:

- EXTERNAL create/stop/snapshot runtime witness.
- INTERNAL create requires entitlement (`403` without `can_use_internal`, `201` with entitlement).
- GPU exclusivity and per-user concurrency limits under concurrency.
- Recovery transitions across `starting|running|stopping` and terminal states.
- Recovery health signaling (`/healthz` degradation and recovery behavior).

Runner:

- `bash ops/host/validate-phase3-lifecycle-recovery.sh`

### Phase 4: Routing, Isolation, End-to-End

Purpose: verify wildcard routing authorization, east-west isolation, and browser transport lane.

Required checks:

- Wildcard root routing authorization matrix (`401` unauthenticated, `403` non-owner, `200` owner).
- Wildcard `/api/v2/auth/session-proxy` path is blocked (`403`) for external callers.
- Client-supplied `X-Upstream` spoof attempt has no routing effect when probing API-host session-proxy.
- East-west isolation blocks direct session-to-session `:8080` access.
- End-to-end runtime flow (GPU visibility, workspace write/read, stop finalization with snapshot).
- Browser wildcard + websocket lane (always required).
- External DNS + TLS + health preflight for canonical web/api hosts.

Runner:

- `bash ops/host/validate-phase4-routing-e2e.sh`

### Phase 5: Competition Platform (Alpha)

Purpose: verify competition APIs, scoring pipeline, and leaderboard behavior.

Required checks:

- Competition catalog and detail contract fields.
- Valid submission scoring with non-null official primary score.
- Invalid submission and missing-resource error contract behavior.
- Daily cap enforcement.
- Deterministic leaderboard ranking and scoring determinism.

Runner:

- `bash ops/host/validate-phase5-competitions.sh`

## Full Progression Runner

Run all phases in order:

- `bash ops/host/validate-policy-remote-external.sh`
- `bash ops/host/validate-phases-all.sh`

The progression runner must stop on first failure.

## Definition of Done

- User can authenticate and create an EXTERNAL GPU session.
- GPU exclusivity and per-user limits are enforced under concurrent requests.
- Session work persists in unique per-session ZFS datasets.
- Stop finalization produces snapshot evidence.
- Recovery logic prevents stranded active sessions and reports health correctly.
- Routing and isolation enforce owner-bound access and block lateral `:8080` traffic.
- Competition flows score submissions with deterministic ranking and enforced daily caps.
