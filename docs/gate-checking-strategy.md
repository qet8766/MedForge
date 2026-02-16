# MedForge Gate Checking Strategy (Canonical)

This is the single source of truth for gate verification strategy, execution order, evidence handling, and operational decision rules.

## Scope and Non-Negotiables

- Gate order is strict: `Gate 0 -> Gate 1 -> Gate 2 -> Gate 3 -> Gate 4 -> Gate 5 -> Gate 6 -> Gate 7`.
- Do not skip gates.
- Do not advance when the current gate is `FAIL` or `INCONCLUSIVE`.
- Runtime truth is required. Tests are supporting evidence, not sufficient by themselves.
- Every run must produce immutable evidence and a clear verdict.

## Runtime Baseline (Current Host Context)

- Single Ubuntu host.
- `7x NVIDIA GeForce RTX 5090`.
- Docker runtime with NVIDIA support.
- ZFS pool: `tank` with MedForge datasets under `tank/medforge/...`.
- Control plane: `medforge-web`, `medforge-api`, `medforge-db`, `medforge-caddy`, `medforge-api-worker`.

## Verdict Vocabulary

- `PASS`: all acceptance checks for the gate succeeded with required evidence.
- `FAIL`: one or more required checks failed.
- `INCONCLUSIVE`: checks were partial, interrupted, or evidence is incomplete.
- `SUPERSEDED`: artifact exists historically but should not be used as canonical proof.

## Evidence and Logging Policy

- Evidence artifacts are immutable once written.
- Long logs are centralized in `docs/validation-logs.md`.
- Canonical pointer table below identifies the latest valid evidence per gate.
- When a new run is accepted, update the canonical pointer table in this file and append full raw output to `docs/validation-logs.md`.

### Canonical Evidence Pointer

| Gate | Latest Evidence | Timestamp (UTC) | Status | Notes |
| --- | --- | --- | --- | --- |
| 0 | `gate0-validation-2026-02-16T103429Z` | `2026-02-16T10:34:31Z` | PASS | Strict GPU/ZFS/DNS/TLS checks completed. |
| 1 | `none` | `n/a` | INCONCLUSIVE | Refresh required under this canonical strategy. |
| 2 | `none` | `n/a` | INCONCLUSIVE | Refresh required under this canonical strategy. |
| 3 | `none` | `n/a` | INCONCLUSIVE | Refresh required under this canonical strategy. |
| 4 | `none` | `n/a` | INCONCLUSIVE | Refresh required under this canonical strategy. |
| 5 | `host-validation-2026-02-16` | `2026-02-16` | PASS | Auth matrix, spoof resistance, and isolation passed. |
| 6 | `host-validation-2026-02-16` | `2026-02-16` | PASS | End-to-end core and browser websocket lane passed. |
| 7 | `none` | `n/a` | INCONCLUSIVE | Refresh required under this canonical strategy. |

### Superseded Artifacts

| Artifact ID | Status | Reason | Replacement |
| --- | --- | --- | --- |
| `gate0-validation-2026-02-16T103320Z` | SUPERSEDED | Report generation defect in first attempt. | `gate0-validation-2026-02-16T103429Z` |

## Execution Modes

- `Witness mode` (default for gate advancement):
  - Run checks step-by-step.
  - Inspect outputs immediately.
  - Record pass/fail per check before moving forward.
- `Script mode` (allowed where stable scripts exist):
  - Use scripted runners (for example `infra/host/validate-gate56.sh --with-browser`).
  - Still require explicit check-by-check verdict extraction and evidence capture.

## Standard Run Record Template

Use this structure for every gate run entry (stored in `docs/validation-logs.md`):

```text
Gate: <N>
Run ID: <gateN-validation-YYYY-MM-DDTHHMMSSZ>
Timestamp UTC: <ISO8601>
Executor: <name or automation id>
Environment:
  domain=<...>
  pack_image=<...>
  runtime_mode=<...>
  compose_services=<...>
Commands:
  - <command 1>
  - <command 2>
Checks:
  - <check name>: expected=<...>, observed=<...>, status=<PASS|FAIL|INCONCLUSIVE>
Verdict:
  gate_status=<PASS|FAIL|INCONCLUSIVE>
  blockers=<...>
```

## Gate Checklists

### Gate 0: Host Foundation

Required checks:

1. Host GPU visibility:
- `nvidia-smi -L`
- `nvidia-smi`

2. GPU container runtime:
- `docker run --rm --gpus all --entrypoint nvidia-smi <PACK_IMAGE>`

3. ZFS health and primitives:
- `zpool list`
- `zpool status tank`
- `zfs list tank/medforge tank/medforge/workspaces tank/medforge/system/db`
- temporary dataset create/write/read/snapshot/list/destroy under `tank/medforge/workspaces`

4. Wildcard DNS:
- resolve `medforge.<domain>`, `api.medforge.<domain>`, `s-<slug>.medforge.<domain>`

5. Strict TLS validation (no `-k`):
- HTTPS reachability checks for base/api/wildcard hosts.
- `openssl s_client -verify_return_error -verify_hostname ...`
- wildcard SAN contains `*.medforge.<domain>`.

Pass criteria:

- All checks pass; otherwise gate fails.

### Gate 1: Control Plane Bootstrap

Required checks:

1. Compose stack:
- `docker compose --env-file infra/compose/.env -f infra/compose/docker-compose.yml up -d --build`
- Verify all core services are healthy/running.

2. API + UI reachability:
- API health endpoint returns success.
- Web root responds successfully.

3. DB + seed readiness:
- `gpu_devices` rows `0..6` enabled.
- default pack exists and digest is pinned.

Pass criteria:

- Services running, API/UI reachable, seed invariants confirmed.

### Gate 2: Auth

Required checks:

1. Signup/login/logout flow with cookie auth.
2. `/api/me` succeeds with valid cookie.
3. Protected path returns `401` without cookie.
4. Cookie scope works across required subdomains.

Pass criteria:

- Correct auth behavior across success and denial paths.

### Gate 3: Session Lifecycle

Required checks:

1. `POST /api/sessions` creates PUBLIC session.
2. `tier=private` returns `501`.
3. GPU allocation exclusivity:
- 8 concurrent create attempts -> 7 success, 1 no-GPU failure.
4. Per-user concurrent limit enforced.
5. Stop endpoint behavior:
- `POST /api/sessions/{id}/stop` returns `202`.
- idempotent responses for repeated stop calls.
6. Snapshot finalization:
- stop path completes via recovery and creates snapshot.

Pass criteria:

- Lifecycle transitions and resource invariants hold under concurrency.

### Gate 4: Fault Recovery

Required checks:

1. Kill running container:
- poller marks session `error` within SLA.
2. API restart reconciliation:
- normalizes `starting/running` rows.
- retries pending `stopping` rows.
3. Health degradation:
- `/healthz` returns `503` when recovery thread unavailable.
- returns `200` when recovered.

Pass criteria:

- No stranded active sessions and recovery health signal is correct.

### Gate 5: Routing and Isolation

Required checks:

1. Auth matrix via wildcard host:
- unauthenticated `401`
- non-owner `403`
- owner `200` with server-generated upstream
2. Header spoof resistance:
- client-supplied `X-Upstream` does not affect routing.
3. East-west isolation:
- session A cannot reach session B `:8080`.

Recommended runner:

- `bash infra/host/validate-gate56.sh --with-browser`

Pass criteria:

- All matrix, spoof, and isolation checks pass.

### Gate 6: End-to-End

Required checks:

1. UI flow:
- login -> create PUBLIC session -> open wildcard session host.
2. In-session runtime:
- `nvidia-smi` succeeds.
- `/workspace` write/read succeeds.
3. Stop and persistence:
- stop requested and finalized.
- snapshot exists after stop.
4. Browser websocket lane:
- terminal websocket traffic observed.

Recommended runner:

- `bash infra/host/validate-gate56.sh --with-browser`

Pass criteria:

- Full user path works with GPU, persistence, and browser transport.

### Gate 7: Competition Portal

Required checks:

1. Competition discovery:
- `GET /api/competitions` includes expected permanent PUBLIC competitions.
2. Valid submission:
- scored successfully with non-null `official_score.primary_score`.
3. Invalid submission:
- returns RFC 7807 style error (`application/problem+json`).
4. Daily cap enforcement:
- overflow request returns `429`.
5. Leaderboard correctness:
- best-per-user ranking with deterministic tie-break.

Pass criteria:

- Competition APIs/UI, scoring, errors, and ranking invariants hold.

## Escalation and Re-run Rules

- If a gate fails due to environment drift, stop progression and remediate first.
- If a run is interrupted or partial, mark `INCONCLUSIVE` and rerun gate fully.
- Use one controlled rerun for suspected transient issues; if it fails again, treat as structural failure.
- Log root cause and remediation steps in `docs/validation-logs.md`.

## Operational Recovery Commands

- Restart all services:
  - `docker compose --env-file infra/compose/.env -f infra/compose/docker-compose.yml restart`
- Restart API only (triggers reconciliation):
  - `docker compose --env-file infra/compose/.env -f infra/compose/docker-compose.yml restart medforge-api`
- Trigger reconciliation helper:
  - `bash infra/host/ops-reconcile.sh`
- Inspect snapshots:
  - `bash infra/host/ops-snapshots.sh`
- Orphan cleanup (dry run / force):
  - `bash infra/host/ops-cleanup.sh`
  - `bash infra/host/ops-cleanup.sh --force`

## Change Control

- Any change to gate acceptance, evidence policy, or progression rules must be made in this file first.
- Historical evidence remains immutable; only canonical pointer rows are updated.
- Long outputs and transcripts belong in `docs/validation-logs.md`.
