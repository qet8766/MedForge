## 8. Implementation Checklist

Purpose: translate the spec into ticket-ready implementation work with explicit state transitions, idempotency rules, and acceptance checks.

### Cross-Cutting Invariants

- `sessions.status` active set is `starting | running | stopping`; terminal set is `stopped | error`.
- GPU lock is enforced only by DB constraint (`UNIQUE(gpu_id, gpu_active)`), where `gpu_active` is non-null only for active states.
- Every session has its own workspace dataset path in `sessions.workspace_zfs` and paths are unique.
- Reconciliation must not leave `starting` rows stranded; `stopping` rows may remain only when stop command execution fails and must be retried by poller.
- `tier=PRIVATE` remains modeled everywhere but `POST /api/v1/sessions` must return `501`.
- Runtime interface uses typed DTO request/result contracts; runtime methods must not accept ORM models (`SessionRecord`, `Pack`).

### API Checklist

#### `POST /api/v1/sessions`

- Require authenticated user.
- Accept `tier` and optional `pack_id`.
- Return `501` when `tier=PRIVATE`.
- Enforce per-user concurrency limit inside the allocation transaction.
- Allocate exactly one enabled GPU, race-safe under concurrent calls.
- Create a session row in `starting` with `workspace_zfs=tank/medforge/workspaces/<user_id>/<session_id>`.
- After transaction commit, provision dataset and start container.
- On success set `running`, `container_id`, `started_at`.
- On failure set `error`, `stopped_at`, and `error_message`.

#### `POST /api/v1/sessions/{id}/stop`

- Require owner or admin.
- Be idempotent for repeated requests.
- Return `202 Accepted`.
- Return action-only payload (`{detail: ...}`), not the full session object.
- Transition `starting` or `running` to `stopping`.
- If already `stopping`, return `Session stop requested.` without changing state.
- If already terminal (`stopped` or `error`), return `Session already terminal.` without changing state.
- Do not execute runtime stop/snapshot in request path; recovery handles completion.

#### `GET /api/v1/auth/session-proxy`

- Parse slug from `Host: s-<slug>.medforge.<domain>`.
- Require valid cookie session.
- Return `200` with `X-Upstream: mf-session-<slug>:8080` only when requester is owner/admin and session is `running`.
- Return `401` for unauthenticated, `403` for unauthorized, `404` for not found or non-running.
- Never trust client-provided `X-Upstream`; only emit server-generated upstream.

### Competition Platform Checklist (Alpha)

#### Invariants

- `competition_tier` means deployment/data policy (`PUBLIC | PRIVATE`), not label visibility.
- Alpha competitions are permanent (`is_permanent=true`) and always `status=active`.
- `scoring_mode` is `single_realtime_hidden`.
- `leaderboard_rule` is `best_per_user`.
- `evaluation_policy` is `canonical_test_first`.
- Scores are stored as append-only `submission_scores` runs; no `final_score` phase in alpha.
- Hidden holdout labels are never mounted in session containers.

#### Competition/Dataset APIs

- `GET /api/v1/competitions` returns active competitions with `competition_tier`, `metric`, `metric_version`, `scoring_mode`, `leaderboard_rule`, `evaluation_policy`, `competition_spec_version`, `is_permanent`, and `submission_cap_per_day`.
- `GET /api/v1/competitions/{slug}` returns dataset linkage and competition metadata.
- `GET /api/v1/datasets` and `GET /api/v1/datasets/{slug}` return mirrored dataset metadata.

#### Submission APIs

- `POST /api/v1/competitions/{slug}/submissions` accepts CSV only, validates competition-specific schema, persists artifact hash/path, and sets `score_status=queued`.
- Enforce daily cap per competition per user (Titanic `20/day`, RSNA `10/day`, CIFAR `20/day`).
- `GET /api/v1/competitions/{slug}/submissions/me` returns submission history with `score_status`, `official_score`, and errors.
- `GET /api/v1/competitions/{slug}/leaderboard` ranks by best per-user official `primary_score`; tie-break by earliest score timestamp then submission ID.

#### Scoring Worker

- Worker transitions `queued -> scoring -> scored|failed`.
- On success, append an official `submission_scores` row with `primary_score`, `score_components_json`, `scorer_version`, `metric_version`, `evaluation_split_version`, and `manifest_sha256`; set submission `scored_at`.
- On failure, persist `score_error` and terminal `failed` state.
- Scoring must be deterministic for same submission + same `metric_version` + same `evaluation_split_version`.
- Scoring manifest must include `evaluation_split_version`, `scoring_mode`, `leaderboard_rule`, `evaluation_policy`, `id_column`, `target_columns`, and `expected_row_count`.

### State Machine Checklist

| Current State | Event | Required Action | Next State |
| --- | --- | --- | --- |
| none | create accepted | insert session row + allocate GPU + set `starting` | `starting` |
| `starting` | container launch success | set `container_id`, set `started_at`, set `running` | `running` |
| `starting` | container launch failure | set `stopped_at`, set `error_message` | `error` |
| `starting` | stop request | set `stopping` | `stopping` |
| `running` | stop request | set `stopping` | `stopping` |
| `stopping` | stop flow complete + snapshot success | set `stopped_at` | `stopped` |
| `stopping` | stop flow complete + snapshot failure | set `stopped_at`, set `error_message` | `error` |
| `stopping` | stop command execution failure | keep pending for retry | `stopping` |
| `running` | poll detects container death | set `stopped_at`, set `error_message` | `error` |
| `starting` | poll sees container running | set `started_at` if null | `running` |
| `starting` | poll sees container absent/exited | set `stopped_at`, set `error_message` | `error` |
| `starting` or `running` | boot reconcile sees running container | normalize status and timestamps | `running` |
| `starting` or `running` | boot reconcile sees absent/exited container | set `stopped_at`, set `error_message` | `error` |
| `stopping` | boot reconcile | finish stop flow (terminate if needed, snapshot, finalize) | `stopped` or `error` |

### Ticket Breakdown

#### Ticket 1: DB Schema + Migration — Done

- Create enums and tables from `docs/data-model.md`.
- Implement generated column `gpu_active`.
- Add `UNIQUE(gpu_id, gpu_active)`.
- Add `UNIQUE(slug)` and `UNIQUE(workspace_zfs)`.
- Seed `gpu_devices` rows `0..6` with `enabled=true`.
- Seed default pack row.

#### Ticket 2: Session Create Transaction — Done

- Implement SQL transaction with `FOR UPDATE` lock on user row.
- Count active sessions for per-user limit.
- Select free enabled GPU row with lock.
- Insert `starting` session row with deterministic `workspace_zfs`.
- Retry on GPU uniqueness collision a fixed number of times.

#### Ticket 3: Workspace Dataset Provisioning — Done

- Ensure parent dataset exists (`tank/medforge/workspaces/<user_id>`).
- Create child dataset for session id (`.../<session_id>`).
- Set ownership `1000:1000`.
- Apply optional quota if configured.
- Surface provisioning failures to create flow and finalize session as `error`.

#### Ticket 4: Container Launch — Done

- Start container name `mf-session-<slug>` on `medforge-public-sessions`.
- Bind exactly one physical GPU via Docker runtime device selection.
- Inject runtime env vars:
- `MEDFORGE_SESSION_ID`
- `MEDFORGE_USER_ID`
- `MEDFORGE_TIER`
- `MEDFORGE_GPU_ID`
- `NVIDIA_VISIBLE_DEVICES`
- `CUDA_VISIBLE_DEVICES=0`
- Mount `workspace_zfs` to `/workspace`.
- Enforce non-root user and hardened container flags from spec.

#### Ticket 5: Stop Flow — Done

- Lock session row and apply compare-and-set transition into `stopping` from `starting` or `running`.
- Return `202 Accepted` from API stop request path (no runtime side effects in request path).
- Execute terminate/snapshot/finalize from recovery worker for `stopping` rows.
- Finalize as `stopped` on stop+snapshot success.
- Finalize as `error` on snapshot failure.
- Keep `stopping` and retry if stop command fails.
- Emit `session.stop` with reason `requested`, `container_death`, or `snapshot_failed`.

#### Ticket 6: Poller — Done

- Run at `SESSION_POLL_INTERVAL_SECONDS` base interval.
- Query sessions in `starting`, `running`, and `stopping`.
- Inspect container process state.
- Retry `unknown` container state a bounded number of times, then finalize `error` if still `unknown`.
- Normalize `starting -> running` when container is up.
- Mark `error` with `stopped_at` when container is gone/exited.
- Emit `session.stop` reason `container_death` when transitioning from active to `error`.
- Complete stop flow for `stopping` rows and retry when stop command fails.
- On poll loop failures, apply exponential backoff capped by `SESSION_POLL_BACKOFF_MAX_SECONDS`, then reset to base interval after a successful poll.
- Report recovery degradation through `GET /healthz` returning `503` when the recovery thread is unavailable; return `200` when healthy.

#### Ticket 7: Boot Reconciliation — Done

- On API startup, scan sessions in `starting | running | stopping`.
- For `starting/running` with running container, normalize to `running`.
- For `starting/running` without running container, mark `error`.
- For `stopping`, run stop completion logic; if stop command fails, leave `stopping` for poller retry.
- Guarantee no rows remain in `starting` after reconciliation pass.

#### Ticket 8: Auth + Wildcard Routing — Done

- Implement `GET /api/v1/auth/session-proxy` contract.
- Ensure Caddy strips inbound `X-Upstream`.
- Fail closed if auth response misses upstream on `200`.
- Preserve websocket upgrades for code-server terminal.

#### Ticket 9: East-West Isolation — Done

- Install `DOCKER-USER` rules to allow only Caddy fixed IP to reach session `:8080`.
- Drop all other sources to session `:8080`.
- Validate from session A that direct access to session B `:8080` fails.

#### Ticket 10: Structured Event Logging — Done

- Emit one JSON line per event to stdout.
- Required events:
- `session.start`
- `session.stop`
- Include identifiers from spec payloads (`session_id`, `user_id`, `tier`, `gpu_id`, `pack_id`, `slug`, `reason`).

### Acceptance Test Checklist

#### Concurrency and Allocation — Validated

- Run 8 parallel create requests with all GPUs enabled; exactly 7 succeed and 1 fails `no GPUs available`.
- Run parallel creates for one user with `max_concurrent_sessions=1`; exactly one succeeds.
- Verify each created session has unique `workspace_zfs`.

#### Lifecycle and Recovery — Validated

- Force container death (`docker kill`) and verify poller marks `error` within 30 seconds.
- Restart API with sessions in mixed active states and verify reconciliation normalizes `starting` rows and retries pending `stopping` rows.
- Simulate snapshot command failure and verify stop finalizes as `error` with message.
- Simulate stop command failure and verify session remains `stopping` and is retried by poller.
- Simulate recovery-thread unavailability and verify `GET /healthz` returns `503`, then returns `200` after thread health is restored.

#### Routing and Isolation — Validated (see `docs/host-validation-2026-02-16.md`)

- Validate owner access `200`, other user `403`, unauthenticated `401`.
- Send malicious client `X-Upstream` and verify it has no routing effect.
- Validate websocket terminal still works through proxy.
- Verify session-to-session direct `:8080` access is blocked.

#### Competition API and Scoring — Validated

- Verify `GET /api/v1/competitions` includes `titanic-survival`, `rsna-pneumonia-detection`, and `cifar-100-classification` with `competition_tier=PUBLIC`.
- Verify all returned competitions include `scoring_mode=single_realtime_hidden`, `leaderboard_rule=best_per_user`, `evaluation_policy=canonical_test_first`, and contract versions (`metric_version`, `competition_spec_version`).
- Submit valid Titanic CSV and verify `score_status=scored` and non-null `official_score.primary_score`.
- Verify Titanic holdout manifest expects 418 labelled test IDs (`evaluation_split_version=v2-kaggle-labelled-test418`).
- Submit invalid schema and verify `422` RFC 7807 payload (`type`, `title`, `status`, `detail`, `instance`) with actionable validation detail.
- Verify competition error responses include `content-type: application/problem+json`.
- Verify missing resources return scoped problem types:
  - competition slug not found -> `competitions/competition-not-found`
  - dataset slug not found -> `competitions/dataset-not-found`
  - admin score on unknown submission -> `competitions/submission-not-found`
- Exhaust daily cap and verify next submission returns `429`.
- Confirm leaderboard returns best score per user and deterministic rank ordering.

### Phase 2: Hardening (MF-101 through MF-105)

#### MF-101: Automated Phase Validation Test Suite — Done

- `tests/test_concurrency.py` — 8-way parallel session create; assert exactly 7 succeed, 8th returns GPU exhaustion error.
- `tests/test_poller_sla.py` — Force container states via `RecoveryRuntime`, verify poller detects within configurable interval.
- `tests/test_auth_hardening.py` — X-Upstream spoof rejection, origin validation matrix, rate limit 429, session fixation, idle/max TTL.
- `tests/test_isolation.py` — Docker-dependent east-west isolation tests (mark `@pytest.mark.docker`).

#### MF-102: Operational Scripts/Runbook — Done

- `ops/host/ops-reconcile.sh` — Trigger manual reconciliation via API service restart.
- `ops/host/ops-snapshots.sh` — List/inspect ZFS snapshots by slug or user.
- `ops/host/ops-cleanup.sh` — Find orphaned `mf-session-*` containers, optionally remove.
- `docs/runbook.md` — Operational procedures: restart, reconcile, inspect, cleanup, escalation.

#### MF-103: Logging Hardening — Done

- `app/main.py` — Bind `request_id` to structlog contextvars in request middleware.
- `app/session_recovery.py` — Bind `correlation_id` and `recovery_mode` to recovery thread logs.
- `app/problem_details.py` — Add centralized `ERROR_CODE_REGISTRY` mapping code → HTTP status + problem type.
- `tests/test_log_schema.py` — Validate required fields (`session_id`, `user_id`, `correlation_id`) in lifecycle log events.

#### MF-104: Security Hardening Pass — Done

- `app/routers/auth.py` — `require_auth_rate_limit` already wired to `/signup` and `/login`.
- `app/deps.py` — Idle TTL and max TTL enforcement already in `_principal_from_cookie()`.
- `tests/test_auth_hardening.py` — Session fixation, idle TTL expiry, max TTL expiry, rate limit 429 tests.

#### MF-105: Soak/Load Pass — Done

- `tests/test_load.py` (mark `@pytest.mark.load`) — 50 sequential + 20 concurrent create/stop cycles.
- `tests/test_chaos.py` — Stop errors, snapshot errors, mixed failure recovery sequences.
- `tests/test_invariants.py` — Post-load assertions: no stuck STARTING, GPU uniqueness, STOPPING resolved, GPU freed.

### Definition of "Implementation Complete"

All criteria met as of 2026-02-16:

- [x] All Phase 1 tickets (1-10) are implemented.
- [ ] Phase acceptance checks rerun and accepted under `docs/phase-checking-strategy.md`.
- [x] No known path leaves a session stuck in an active non-running state.
- [x] Phase 2 hardening (MF-101 to MF-105) complete: 112 total tests, operational scripts, runbook.
