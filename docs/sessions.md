## Sessions

> V2 Update (2026-02-17): Canonical session APIs are split by exposure:
> - `POST /api/v2/external/sessions`, `GET /api/v2/external/sessions/current`, `POST /api/v2/external/sessions/{id}/stop`
> - `POST /api/v2/internal/sessions`, `GET /api/v2/internal/sessions/current`, `POST /api/v2/internal/sessions/{id}/stop` (requires `can_use_internal`)
> Runtime env uses `MEDFORGE_EXPOSURE=EXTERNAL|INTERNAL`.

Implementation status note (2026-02-17):

- Core Phase 3 flow is implemented for EXTERNAL and INTERNAL exposure routes:
  - `POST /api/v2/external/sessions` and `POST /api/v2/internal/sessions` perform allocation + launch.
  - `POST /api/v2/external/sessions/{id}/stop` and `POST /api/v2/internal/sessions/{id}/stop` are idempotent async stop requests (`202`).
  - `GET /api/v2/external/sessions/current` and `GET /api/v2/internal/sessions/current` return the caller's most recent active session.
  - `apps/web/app/sessions/page.tsx` rehydrates session state on load and after create/stop actions.
- Phase 3 recovery paths are implemented:
  - boot-time reconciliation for `starting|running|stopping`
  - active-session poller for `starting|running|stopping` transitions
- Runtime internals are split into `app/session_runtime/` ports/adapters with DTO-based method contracts (no ORM models in runtime API).
- Historical pre-phase host evidence was retired from the repo; canonical progression uses `@docs/phase-checking-strategy.md`.

### Scope

### In Scope

- session create/stop/current endpoint behavior and invariants
- runtime container contract (naming, network, mounts, env injection)
- asynchronous stop finalization and recovery/poller behavior
- session health and reconciliation behavior

### Out of Scope

- auth cookie and wildcard forward-auth contract (`@docs/auth-routing.md`)
- schema/table definitions (`@apps/api/app/models.py`, `@apps/api/alembic/versions/`)

### Canonical Sources

- `@apps/api/app/routers/control_plane.py`
- `@apps/api/app/session_lifecycle.py`
- `@apps/api/app/session_recovery.py`
- `@apps/api/app/session_runtime/`

### Packs

One default Pack, pinned by image digest. code-server version pinned globally. The target model includes `packs` and `sessions.pack_id`; UI does not expose pack selection.

### Container Spec

Image definition: `@deploy/packs/default/Dockerfile`

Runtime constraints (applied by the session manager when creating the container):

- `--auth none` on code-server (Caddy is the access boundary).
- Non-root user (UID/GID 1000).
- `cap-drop=ALL`, not privileged, no Docker socket.
- `security_opt=["no-new-privileges:true"]`
- Container name: `mf-session-<slug>`
- Network: `medforge-external-sessions`

Mounts:

| Container path | Host source                               |
| -------------- | ----------------------------------------- |
| `/workspace`   | ZFS dataset for the session (`tank/medforge/workspaces/<user_id>/<session_id>`) |

Environment variables injected at runtime:

```
MEDFORGE_SESSION_ID=<uuid>
MEDFORGE_USER_ID=<uuid>
MEDFORGE_EXPOSURE=EXTERNAL|INTERNAL
MEDFORGE_GPU_ID=<gpu_id>
NVIDIA_VISIBLE_DEVICES=<gpu_idx>
CUDA_VISIBLE_DEVICES=0
```

Optional runtime toggle:

- `SESSION_RUNTIME_USE_SUDO=true` runs ZFS/chown shell commands via `sudo -n` (useful when API process is not root on host installs).
- `SESSION_RUNTIME_MODE=mock|docker` chooses runtime assembly in `app/session_runtime/factory.py`.

### Session Lifecycle

#### Create -- `POST /api/v2/external/sessions` or `POST /api/v2/internal/sessions`

Inputs: optional `pack_id` (defaults to seeded pack).
- Every session allocates exactly one GPU.
- If an `Origin` header is present, it must match an allowed MedForge remote-external origin or the API returns **403**.

**Race-safe allocation (single transaction):**

1. `BEGIN`
2. Lock user row: `SELECT * FROM users WHERE id=:user_id FOR UPDATE`
3. Count user active sessions (`starting | running | stopping`). If >= `max_concurrent_sessions`, reject.
4. Select a free enabled GPU and lock it (`FOR UPDATE`). Pick an enabled `gpu_devices.id` not assigned to an active session.
5. Insert session row: `status='starting'`, chosen `gpu_id`, `slug`, `pack_id`, and `workspace_zfs=tank/medforge/workspaces/<user_id>/<session_id>`.
6. If insert fails due to an integrity conflict (for example slug/workspace uniqueness), roll back and retry a fixed number of times.
7. `COMMIT`

**After commit, spawn container:**

- Ensure session workspace dataset exists at `workspace_zfs`, set owner to UID/GID 1000:1000, and apply optional quota.
- Name: `mf-session-<slug>`
- Network: `medforge-external-sessions`
- Mount: `/workspace` from session dataset (`workspace_zfs`)
- GPU: Docker runtime device binding to one physical GPU (`--gpus "device=<gpu_idx>"`) plus env vars above for in-container visibility

Update session: set `container_id`, `status='running'`, `started_at`. On failure (dataset create or container start): set `status='error'`, `stopped_at`, `error_message`. Leaving active status makes the GPU available for subsequent allocations because allocator selection excludes non-terminal active rows.

#### Stop -- `POST /api/v2/external/sessions/{id}/stop` or `POST /api/v2/internal/sessions/{id}/stop`

If an `Origin` header is present, it must match an allowed MedForge remote-external origin or the API returns **403**.

1. If row is `starting` or `running`, set `status='stopping'` and return **202** with `{message:"Session stop requested."}`.
2. If row is already `stopping`, return **202** with the same message (idempotent intent).
3. If row is terminal (`stopped` or `error`), return **202** with `{message:"Session already terminal."}`.
4. Runtime stop/snapshot is not executed in request path.
5. Recovery loop finalizes `stopping` rows:
   - stop + snapshot success -> `stopped`, set `stopped_at`.
   - stop success + snapshot failure -> `error`, set `stopped_at`, set `error_message`.
   - stop command failure -> remain `stopping` and retry on later recovery pass.
6. Clients read session state from the matching exposure route (`GET /api/v2/external/sessions/current` or `GET /api/v2/internal/sessions/current`) after issuing stop.

#### Read Current -- `GET /api/v2/external/sessions/current` or `GET /api/v2/internal/sessions/current`

- Auth required (`/api/v2/me` auth model).
- Returns envelope payload:
  - `{ "data": { "session": SessionRead | null }, "meta": { ... } }`
- Only the caller's own sessions are considered.
- The selected row is the newest active session (`starting|running|stopping`) by `created_at DESC`.

#### Session Proxy Contract -- `GET /api/v2/auth/session-proxy`

- This endpoint is internal control-plane plumbing for Caddy `forward_auth`.
- External wildcard callers to `https://s-<slug>.medforge.<domain>/api/v2/auth/session-proxy` are blocked with **403**.
- Real owner-access validation should target wildcard session root (`https://s-<slug>.medforge.<domain>/`) rather than calling this internal path directly.

#### Container State Poller (`SESSION_POLL_INTERVAL_SECONDS` base interval)

- Query sessions with `status IN ('starting', 'running', 'stopping')`.
- `docker inspect` container state.
- If state is `unknown`, retry inspect a bounded number of times (hard-coded constant `UNKNOWN_STATE_MAX_RETRIES = 3` in `app/session_recovery.py`, with `0.25s` delay between retries); if still unknown, mark `error`.
- If running and status is `starting`: set `status='running'` and ensure `started_at` is set.
- If not running: set `status='error'`, `stopped_at`, `error_message="container exited unexpectedly"`; emit `session.stop` event with `reason: container_death`.
- If status is `stopping`: execute stop completion flow (stop + snapshot -> `stopped`/`error`; stop command failure leaves `stopping`).
- Polling uses exponential backoff after poll-loop failures, capped by `SESSION_POLL_BACKOFF_MAX_SECONDS`, and resets to the base interval after a successful poll.

#### API Health

- `GET /healthz` returns `200` when API + recovery loop are healthy.
- `GET /healthz` returns `503` when recovery is enabled but the recovery thread is unavailable.
- Health payload uses the same envelope contract: `{ "data": { "status": "ok" | "degraded" }, "meta": { ... } }`.

#### Boot-Time Reconciliation

On medforge-api startup, reconcile sessions in `starting | running | stopping`:

- If container is running and status is `starting` or `running`: set `status='running'` and ensure `started_at` is set.
- If status is `stopping`: run stop completion flow.
- If container is missing/not running and status is `starting` or `running`: set `status='error'`, `stopped_at`, and `error_message`.

Reconciliation can leave `stopping` rows when stop command execution fails; poll loop retries those rows.

### Event Logging

One JSON object per line to stdout.

| Event           | Payload                                              |
| --------------- | ---------------------------------------------------- |
| `session.start` | `{session_id, user_id, exposure, gpu_id, pack_id, slug}` |
| `session.stop`  | `{reason: requested \| container_death \| snapshot_failed}` |
