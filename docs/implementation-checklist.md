## 8. Implementation Checklist

Purpose: translate the spec into ticket-ready implementation work with explicit state transitions, idempotency rules, and acceptance checks.

### Cross-Cutting Invariants

- `sessions.status` active set is `starting | running | stopping`; terminal set is `stopped | error`.
- GPU lock is enforced only by DB constraint (`UNIQUE(gpu_id, gpu_active)`), where `gpu_active` is non-null only for active states.
- Every session has its own workspace dataset path in `sessions.workspace_zfs` and paths are unique.
- No session may remain in `starting` or `stopping` after reconciliation finishes.
- `tier=PRIVATE` remains modeled everywhere but `POST /api/sessions` must return `501`.

### API Checklist

#### `POST /api/sessions`

- Require authenticated user.
- Accept `tier` and optional `pack_id`.
- Return `501` when `tier=PRIVATE`.
- Enforce per-user concurrency limit inside the allocation transaction.
- Allocate exactly one enabled GPU, race-safe under concurrent calls.
- Create a session row in `starting` with `workspace_zfs=tank/medforge/workspaces/<user_id>/<session_id>`.
- After transaction commit, provision dataset and start container.
- On success set `running`, `container_id`, `started_at`.
- On failure set `error`, `stopped_at`, and `error_message`.

#### `POST /api/sessions/{id}/stop`

- Require owner or admin.
- Be idempotent for repeated requests.
- Transition `starting` or `running` to `stopping`, terminate container, snapshot dataset, then finalize.
- On snapshot success finalize `stopped` with `stopped_at`.
- On snapshot failure finalize `error` with `stopped_at` and `error_message`.
- If already terminal (`stopped` or `error`), return current state without changing it.

#### `GET /api/auth/session-proxy`

- Parse slug from `Host: s-<slug>.medforge.<domain>`.
- Require valid cookie session.
- Return `200` with `X-Upstream: mf-session-<slug>:8080` only when requester is owner/admin and session is `running`.
- Return `401` for unauthenticated, `403` for unauthorized, `404` for not found or non-running.
- Never trust client-provided `X-Upstream`; only emit server-generated upstream.

### Competition Platform Checklist (Alpha)

#### Invariants

- `competition_tier` means deployment/data policy (`PUBLIC | PRIVATE`), not label visibility.
- Alpha competitions are permanent (`is_permanent=true`) and always `status=active`.
- Only `leaderboard_score` is published; no `final_score` phase in alpha.
- Hidden holdout labels are never mounted in session containers.

#### Competition/Dataset APIs

- `GET /api/competitions` returns active competitions with `competition_tier`, `metric`, `is_permanent`, and `submission_cap_per_day`.
- `GET /api/competitions/{slug}` returns dataset linkage and competition metadata.
- `GET /api/datasets` and `GET /api/datasets/{slug}` return mirrored dataset metadata.

#### Submission APIs

- `POST /api/competitions/{slug}/submissions` accepts CSV only, validates competition-specific schema, persists artifact hash/path, and sets `score_status=queued`.
- Enforce daily cap per competition per user (Titanic `20/day`, RSNA `10/day`).
- `GET /api/competitions/{slug}/submissions/me` returns submission history with `score_status`, `leaderboard_score`, and errors.
- `GET /api/competitions/{slug}/leaderboard` ranks by best per-user `leaderboard_score`; tie-break by earliest `created_at`.

#### Scoring Worker

- Worker transitions `queued -> scoring -> scored|failed`.
- On success, persist `leaderboard_score`, `scorer_version`, `evaluation_split_version`, and `scored_at`.
- On failure, persist `score_error` and terminal `failed` state.
- Scoring must be deterministic for same submission + same `evaluation_split_version`.

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
| `running` | poll detects container death | set `stopped_at`, set `error_message` | `error` |
| `starting` | poll sees container running | set `started_at` if null | `running` |
| `starting` | poll sees container absent/exited | set `stopped_at`, set `error_message` | `error` |
| `starting` or `running` | boot reconcile sees running container | normalize status and timestamps | `running` |
| `starting` or `running` | boot reconcile sees absent/exited container | set `stopped_at`, set `error_message` | `error` |
| `stopping` | boot reconcile | finish stop flow (terminate if needed, snapshot, finalize) | `stopped` or `error` |

### Ticket Breakdown

#### Ticket 1: DB Schema + Migration

- Create enums and tables from `docs/data-model.md`.
- Implement generated column `gpu_active`.
- Add `UNIQUE(gpu_id, gpu_active)`.
- Add `UNIQUE(slug)` and `UNIQUE(workspace_zfs)`.
- Seed `gpu_devices` rows `0..6` with `enabled=true`.
- Seed default pack row.

#### Ticket 2: Session Create Transaction

- Implement SQL transaction with `FOR UPDATE` lock on user row.
- Count active sessions for per-user limit.
- Select free enabled GPU row with lock.
- Insert `starting` session row with deterministic `workspace_zfs`.
- Retry on GPU uniqueness collision a fixed number of times.

#### Ticket 3: Workspace Dataset Provisioning

- Ensure parent dataset exists (`tank/medforge/workspaces/<user_id>`).
- Create child dataset for session id (`.../<session_id>`).
- Set ownership `1000:1000`.
- Apply optional quota if configured.
- Surface provisioning failures to create flow and finalize session as `error`.

#### Ticket 4: Container Launch

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

#### Ticket 5: Stop Flow

- Lock session row and apply compare-and-set transition into `stopping` from `starting` or `running`.
- Terminate container with grace period then force-kill if needed.
- Snapshot `<workspace_zfs>@stop-<unixms>`.
- Finalize as `stopped` on success.
- Finalize as `error` on snapshot failure.
- Emit `session.stop` with reason `user`, `admin`, or `snapshot_failed`.

#### Ticket 6: Poller

- Run every 30 seconds.
- Query sessions in `starting` and `running`.
- Inspect container process state.
- Normalize `starting -> running` when container is up.
- Mark `error` with `stopped_at` when container is gone/exited.
- Emit `session.stop` reason `container_death` when transitioning from active to `error`.

#### Ticket 7: Boot Reconciliation

- On API startup, scan sessions in `starting | running | stopping`.
- For `starting/running` with running container, normalize to `running`.
- For `starting/running` without running container, mark `error`.
- For `stopping`, run full stop completion logic and finalize to terminal state.
- Guarantee no rows remain in `starting` or `stopping` after reconciliation pass.

#### Ticket 8: Auth + Wildcard Routing

- Implement `GET /api/auth/session-proxy` contract.
- Ensure Caddy strips inbound `X-Upstream`.
- Fail closed if auth response misses upstream on `200`.
- Preserve websocket upgrades for code-server terminal.

#### Ticket 9: East-West Isolation

- Install `DOCKER-USER` rules to allow only Caddy fixed IP to reach session `:8080`.
- Drop all other sources to session `:8080`.
- Validate from session A that direct access to session B `:8080` fails.

#### Ticket 10: Structured Event Logging

- Emit one JSON line per event to stdout.
- Required events:
- `user.login`
- `session.start`
- `session.stop`
- Include identifiers from spec payloads (`session_id`, `user_id`, `tier`, `gpu_id`, `pack_id`, `slug`, `reason`).

### Acceptance Test Checklist

#### Concurrency and Allocation

- Run 8 parallel create requests with all GPUs enabled; exactly 7 succeed and 1 fails `no GPUs available`.
- Run parallel creates for one user with `max_concurrent_sessions=1`; exactly one succeeds.
- Verify each created session has unique `workspace_zfs`.

#### Lifecycle and Recovery

- Force container death (`docker kill`) and verify poller marks `error` within 30 seconds.
- Restart API with sessions in mixed active states and verify reconciliation leaves only `running`, `stopped`, or `error`.
- Simulate snapshot command failure and verify stop finalizes as `error` with message.

#### Routing and Isolation

- Validate owner access `200`, other user `403`, unauthenticated `401`.
- Send malicious client `X-Upstream` and verify it has no routing effect.
- Validate websocket terminal still works through proxy.
- Verify session-to-session direct `:8080` access is blocked.

#### Competition API and Scoring

- Verify `GET /api/competitions` includes `titanic-survival` and `rsna-pneumonia-detection` with `competition_tier=PUBLIC`.
- Submit valid Titanic CSV and verify `score_status=scored` and non-null `leaderboard_score`.
- Submit invalid schema and verify `422` with actionable validation error.
- Exhaust daily cap and verify next submission returns `429`.
- Confirm leaderboard returns best score per user and deterministic rank ordering.

### Definition of "Implementation Complete"

- All tickets above are implemented.
- Gate acceptance checks in `docs/build-gates.md` pass.
- No known path leaves a session stuck in an active non-running state.
