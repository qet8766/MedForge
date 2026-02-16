## 4. Sessions

Implementation status note (2026-02-16):

- Core Gate 3 alpha flow is implemented for PUBLIC sessions:
  - `POST /api/sessions` performs allocation + launch and returns running/error terminalization.
  - `POST /api/sessions/{id}/stop` performs stop + snapshot and is idempotent for terminal states.
- Gate 4 recovery paths are implemented:
  - boot-time reconciliation for `starting|running|stopping`
  - active-session poller for `starting|running` container state transitions
- Host evidence confirms GPU/session create-stop-snapshot behavior on this machine (`@docs/host-validation-2026-02-16.md`).

### Packs

One default Pack, pinned by image digest. code-server version pinned globally. The target model includes `packs` and `sessions.pack_id`; UI does not expose pack selection.

### Container Spec

Image definition: `@infra/packs/default/Dockerfile`

Runtime constraints (applied by the session manager when creating the container):

- `--auth none` on code-server (Caddy is the gate).
- Non-root user (UID/GID 1000).
- `cap-drop=ALL`, not privileged, no Docker socket.
- Container name: `mf-session-<slug>`
- Network: `medforge-public-sessions`

Mounts:

| Container path | Host source                               |
| -------------- | ----------------------------------------- |
| `/workspace`   | ZFS dataset for the session (`tank/medforge/workspaces/<user_id>/<session_id>`) |

Environment variables injected at runtime:

```
MEDFORGE_SESSION_ID=<uuid>
MEDFORGE_USER_ID=<uuid>
MEDFORGE_TIER=PUBLIC|PRIVATE
MEDFORGE_GPU_ID=<gpu_id>
NVIDIA_VISIBLE_DEVICES=<gpu_idx>
CUDA_VISIBLE_DEVICES=0
```

Optional runtime toggle:

- `SESSION_RUNTIME_USE_SUDO=true` runs ZFS/chown shell commands via `sudo -n` (useful when API process is not root on host installs).

### Session Lifecycle

#### Create -- `POST /api/sessions`

Inputs: `tier` (PUBLIC | PRIVATE), optional `pack_id` (defaults to seeded pack).

- `tier=PRIVATE` returns **501**.
- Every session allocates exactly one GPU.

**Race-safe allocation (single transaction):**

1. `BEGIN`
2. Lock user row: `SELECT * FROM users WHERE id=:user_id FOR UPDATE`
3. Count user active sessions (`starting | running | stopping`). If >= `max_concurrent_sessions`, reject.
4. Select a free enabled GPU and lock it (`FOR UPDATE`). Pick an enabled `gpu_devices.id` not assigned to an active session.
5. Insert session row: `status='starting'`, chosen `gpu_id`, `slug`, `pack_id`, and `workspace_zfs=tank/medforge/workspaces/<user_id>/<session_id>`.
6. If insert fails due to `UNIQUE(gpu_id, gpu_active)` conflict, retry a fixed number of times.
7. `COMMIT`

**After commit, spawn container:**

- Ensure session workspace dataset exists at `workspace_zfs`, set owner to UID/GID 1000:1000, and apply optional quota.
- Name: `mf-session-<slug>`
- Network: `medforge-public-sessions`
- Mount: `/workspace` from session dataset (`workspace_zfs`)
- GPU: Docker runtime device binding to one physical GPU (`--gpus "device=<gpu_idx>"`) plus env vars above for in-container visibility

Update session: set `container_id`, `status='running'`, `started_at`. On failure (dataset create or container start): set `status='error'`, `stopped_at`, `error_message`. Leaving active status frees the GPU automatically (generated column becomes NULL, unique constraint releases).

#### Stop -- `POST /api/sessions/{id}/stop`

1. Set `status='stopping'`.
2. SIGTERM container, wait up to 30s.
3. Force-kill if still running.
4. Snapshot workspace dataset: `<workspace_zfs>@stop-<unixms>`.
5. If snapshot succeeds: set `status='stopped'`, `stopped_at`.
6. If snapshot fails: set `status='error'`, `stopped_at`, `error_message="snapshot failed: <details>"`.

#### Container State Poller (every 30s)

- Query sessions with `status IN ('starting', 'running')`.
- `docker inspect` container state.
- If running and status is `starting`: set `status='running'` and ensure `started_at` is set.
- If not running: set `status='error'`, `stopped_at`, `error_message="container exited unexpectedly"`; emit `session.stop` event with `reason: container_death`.

#### Boot-Time Reconciliation

On medforge-api startup, reconcile sessions in `starting | running | stopping`:

- If container is running and status is `starting` or `running`: set `status='running'` and ensure `started_at` is set.
- If status is `stopping`: complete stop flow (terminate if still running, then snapshot, then set `stopped`; if snapshot fails, set `error`).
- If container is missing/not running and status is `starting` or `running`: set `status='error'`, `stopped_at`, and `error_message`.

Reconciliation must leave every examined session in either `running`, `stopped`, or `error` (never stranded in `starting`/`stopping`).

### Event Logging

One JSON object per line to stdout.

| Event           | Payload                                              |
| --------------- | ---------------------------------------------------- |
| `user.login`    |                                                      |
| `session.start` | `{session_id, user_id, tier, gpu_id, pack_id, slug}` |
| `session.stop`  | `{reason: user \| admin \| container_death \| snapshot_failed}` |
