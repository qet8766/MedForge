## 7. Build Gates & Definition of Done

Implementation status note (2026-02-16):

- Gate 7 competition API/UI is implemented and tested in this repo.
- Gate 2 auth endpoints are implemented (`/api/auth/signup`, `/api/auth/login`, `/api/auth/logout`, `/api/me`) with cookie sessions and an optional `X-User-Id` legacy fallback flag.
- Gate 3 alpha lifecycle is implemented for PUBLIC (`/api/sessions`, `/api/sessions/{id}/stop`) with transaction-safe allocation, runtime launch, and snapshot-on-stop terminalization.
- Gate 4 recovery logic (poller + startup reconciliation) is implemented in API and covered by tests.
- Gate 5/6 host evidence run completed via `bash infra/host/validate-gate56.sh --with-browser` for API auth matrix, spoof resistance, east-west block, GPU visibility, workspace write, snapshot-on-stop, Caddy wildcard browser routing, and websocket frame activity (`@docs/host-validation-2026-02-16.md`).

### Gate 0 -- Host Foundation

Docker + NVIDIA Container Toolkit. ZFS pool ready (`@infra/zfs/setup.sh`). DNS wildcard + wildcard TLS via Caddy DNS challenge.

**Acceptance:** GPU container runs CUDA successfully. ZFS read/write works. `*.medforge.<domain>` has valid TLS.

### Gate 1 -- Control Plane Bootstrap

Compose stack up (`@infra/compose/docker-compose.yml`). Networks created (control + public + private placeholder). DB migrations create tables with seed rows.

**Acceptance:** UI + API reachable. Seeded pack exists. `gpu_devices` rows 0-6 exist, all enabled.

### Gate 2 -- Auth

Signup/login, cookie sessions, `/api/me`. forward_auth endpoint for session proxy.

**Acceptance:** Cookie works across subdomains. Protected route returns 401 without cookie.

### Gate 3 -- Session Lifecycle

`POST /api/sessions` creates GPU-only PUBLIC session (PRIVATE returns 501). Transaction-safe GPU allocation. Stop endpoint + ZFS snapshot-on-stop.

**Acceptance:** 7 concurrent sessions succeed; 8th fails "no GPUs available". Per-user limit enforced under concurrent requests. Each created session has a distinct `workspace_zfs` dataset path. Session stop produces a ZFS snapshot. If snapshot creation fails, session ends in `error` (not stranded in `stopping`).

### Gate 4 -- Fault Recovery

Container state poller detects dead containers. Boot-time reconciliation frees stranded sessions.

**Acceptance:** Abrupt container kill (`docker kill`) is detected and marked `error` within 30s at the base poll interval (`SESSION_POLL_INTERVAL_SECONDS`), with failure backoff capped by `SESSION_POLL_BACKOFF_MAX_SECONDS`. API restart reconciles all orphaned sessions to terminal states (`running`, `stopped`, or `error`) with no rows left in `starting`/`stopping`. `GET /healthz` returns `503` when recovery is enabled but its thread is unavailable, and `200` when healthy.

### Gate 5 -- Routing & Isolation

Caddy wildcard route proxies to running sessions (`@infra/caddy/Caddyfile`). East-west isolation enforced (`@infra/firewall/setup.sh`).

**Acceptance:** Owner can access their session; other user gets 403; unauthenticated gets 401. Client-supplied `X-Upstream` headers cannot influence routing (header is stripped, auth still enforced). From inside a session, cannot reach another session's :8080. code-server terminal websockets work.

**Host validation commands (example):**

- `bash infra/host/validate-gate56.sh --with-browser`
- `curl -i -H "Host: s-<slug>.medforge.<domain>" https://api.medforge.<domain>/api/auth/session-proxy`
- `docker exec -it mf-session-<slugA> curl -sS --max-time 3 http://mf-session-<slugB>:8080`

Use `--with-browser` for complete Gate 5 coverage (wildcard browser routing + websocket traffic checks); running without it only covers the API/core lane.

### Gate 6 -- End-to-End

Full user flow through the UI: log in, create a PUBLIC session, land in code-server, run a CUDA program in the terminal, stop the session, verify ZFS snapshot exists.

**Acceptance:** The entire flow completes without manual intervention. GPU is visible inside the session (`nvidia-smi`). The session mounts its own workspace dataset path and writes are persisted there. Snapshot is present after stop.

**Host validation commands (example):**

- `bash infra/host/validate-gate56.sh --with-browser`
- `docker exec -it mf-session-<slug> nvidia-smi`
- `docker exec -it mf-session-<slug> sh -lc 'echo alpha > /workspace/alpha.txt && cat /workspace/alpha.txt'`
- `zfs list -t snapshot | grep "tank/medforge/workspaces/.*/<session_id>@stop-"`

Use `--with-browser` for end-to-end UI/browser verification; without it, only the non-browser core checks are exercised.

### Gate 7 -- Competition Portal (Alpha)

Permanent PUBLIC competitions are available in web + API (`titanic-survival`, `rsna-pneumonia-detection`, `cifar-100-classification`). Users can upload predictions, receive scores, and view ranked leaderboards.

**Acceptance:** `GET /api/competitions` returns all competition slugs with `competition_tier=PUBLIC`, `is_permanent=true`, `scoring_mode=single_realtime_hidden`, `leaderboard_rule=best_per_user`, `evaluation_policy=canonical_test_first`, and explicit contract versions (`metric_version`, `competition_spec_version`). Valid CSV submission returns `score_status=scored` and non-null `official_score.primary_score`. Daily caps are enforced (`20/day` Titanic, `10/day` RSNA, `20/day` CIFAR). Leaderboard ranks by best per-user official `primary_score` with deterministic tie-break by earliest score timestamp and submission ID. Titanic scoring uses the full labelled Kaggle test IDs (`418`) as hidden realtime holdout.

### Definition of Done

- A user can log in, start a PUBLIC GPU session, and access code-server at `s-<slug>.medforge.<domain>`.
- GPU exclusivity is enforced by DB constraint and race-safe allocation.
- Per-user concurrent session limits are enforced.
- Work persists in per-session ZFS datasets and snapshots occur on stop.
- Poller + boot-time reconciliation prevents stranded sessions/GPU locks after failures/restarts.
- PRIVATE exists in enums/policies/networks but session creation returns 501.
- Permanent competition flows are available with hidden-holdout official `primary_score` runs and daily submission cap enforcement.
