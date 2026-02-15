# MedForge Platform Specification

> PUBLIC-first. PRIVATE is fully represented in the data model and policy surface, but `tier=PRIVATE` session creation returns **501 Not Available**.
> Single Ubuntu host with **7x RTX 5090**. Browser IDE = **code-server**.

---

## 1. Overview

MedForge provisions per-user, GPU-backed development sessions (code-server in the browser) on a single multi-GPU Ubuntu host. Sessions run in a single default immutable Pack (Docker image digest pinned) to avoid dependency drift. User work persists on ZFS with snapshots-on-stop for rollback.

### Goals

- Launch PUBLIC sessions: browser VS Code (code-server) + terminal + GPU access.
- Enforce 1 GPU per session and max 7 concurrent sessions (one per physical GPU).
- Enforce per-user concurrent session limits.
- Wildcard subdomains per session: `s-<slug>.medforge.<domain>`.
- Persist per-user workspaces on ZFS; take a snapshot on session stop.
- Structured JSON event logs to stdout (login + session lifecycle).

### Constraints

- Single host (Ubuntu 24.04 LTS).
- Stack: **Next.js + TypeScript**, **FastAPI + SQLModel**, **MariaDB**.
- code-server is the in-browser IDE.
- PRIVATE tier defined but returns 501; no egress restrictions, audited access, or UI transfer controls enforced.

### Non-Goals

- Competitions, forums, marketplace.
- Dataset registry / managed read-only mounts.
- Exfiltration prevention against screenshots/copying.
- Enterprise auth (SSO/SCIM).
- Multi-node scheduling.
- Lease TTL/heartbeat renewal (explicit stop + container state polling + boot-time reconciliation only).
- Scheduled snapshot policies / retention automation.
- Snapshot restore tooling (manual admin ZFS ops only).
- Observability stack beyond structured API logs + host tools.

---

## 2. Architecture

### Control Plane

| Component        | Role                                     |
| ---------------- | ---------------------------------------- |
| **medforge-web** | Next.js frontend                         |
| **medforge-api** | FastAPI + session manager module         |
| **MariaDB**      | Persistent state                         |
| **Caddy**        | Reverse proxy + wildcard TLS + auth gate |

### Data Plane

- Per-session Docker containers running code-server.
- Persistent user workspaces mounted from ZFS.

Full control-plane composition: `@infra/compose/docker-compose.yml`

### Docker Networking

| Network                      | Purpose                          |
| ---------------------------- | -------------------------------- |
| `medforge-control`           | web <-> api <-> db               |
| `medforge-public-sessions`   | PUBLIC session containers        |
| `medforge-private-sessions`  | Placeholder, unused              |

Caddy connects to both `medforge-control` (to reach medforge-api) and `medforge-public-sessions` (to reach session containers by hostname). Caddy is assigned a fixed IP (`172.30.0.2`) on the sessions network for firewall rules.

### Tiers

| Aspect             | PUBLIC                               | PRIVATE               |
| ------------------ | ------------------------------------ | --------------------- |
| Internet egress    | Allowed                              | Blocked               |
| UI upload/download | Allowed                              | Blocked               |
| Data ingestion     | Users fetch data themselves (`wget`) | Controlled            |
| Audit              | Structured JSON logs to stdout       | Strict auditing       |
| Status             | **Available**                        | **501 Not Available** |

### Domains & TLS

| Subdomain                    | Target            |
| ---------------------------- | ----------------- |
| `medforge.<domain>`          | Next.js           |
| `api.medforge.<domain>`      | FastAPI           |
| `s-<slug>.medforge.<domain>` | Session container |

Wildcard cert `*.medforge.<domain>` via Caddy DNS challenge. Single wildcard cert, no per-session issuance. Routing config: `@infra/caddy/Caddyfile`

### Repo Layout

```
apps/
  web/                  # Next.js
  api/                  # FastAPI + SQLModel + session manager
    migrations/         # Alembic
infra/
  caddy/                # Caddyfile, Caddy Dockerfile (DNS plugin)
  compose/              # docker-compose, .env.example
  packs/
    default/            # Session container Dockerfile
  zfs/                  # ZFS pool/dataset setup
  firewall/             # East-west isolation iptables rules
scripts/                # Host bootstrap and common ops
```

---

## 3. Authentication & Routing

### Cookie Sessions

HTTP-only cookie session auth.

- Cookie attributes: `HttpOnly; Secure; SameSite=Lax; Domain=.medforge.<domain>; Path=/`
- CSRF/Origin guard: for all state-changing endpoints, reject if `Origin` is not an allowed MedForge origin.
- Cookie stores a random token (base64url). DB stores only a hash of the token (never raw).

### Wildcard Session Routing (Caddy + forward_auth)

Full Caddy config: `@infra/caddy/Caddyfile`

**forward_auth endpoint:** `GET /api/auth/session-proxy`

Inputs:

- `Host: s-<slug>.medforge.<domain>`
- Cookie session

FastAPI returns:

| Code | Condition                                                  | Header                               |
| ---- | ---------------------------------------------------------- | ------------------------------------ |
| 200  | Authenticated, owns session (or admin), session is running | `X-Upstream: mf-session-<slug>:8080` |
| 401  | Not authenticated                                          |                                      |
| 403  | Authenticated but not owner/admin                          |                                      |
| 404  | Slug not found or session not running                      |                                      |

Caddy behaviour:

- Strips inbound `X-Upstream` from client request (prevents spoofing).
- Fails closed with 502 if `X-Upstream` is missing after auth.
- Proxies websockets natively (code-server terminal).

### East-West Isolation

Session containers must not reach other session containers' port 8080 over the Docker network. code-server runs with `--auth none`; Caddy/forward_auth is the only gate.

Firewall script: `@infra/firewall/setup.sh`

Rules applied to the `DOCKER-USER` chain:

- ALLOW TCP dport 8080 from Caddy's fixed IP (`172.30.0.2`) to the sessions bridge.
- DROP all other sources to TCP dport 8080 on the sessions bridge.

**Acceptance test:** from inside session A, `curl http://mf-session-<slugB>:8080` must fail.

---

## 4. Sessions

### Packs

One default Pack, pinned by image digest. code-server version pinned globally. The `packs` table and `sessions.pack_id` exist; the single Pack row is seeded during migration/init. UI does not expose pack selection.

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
| `/workspace`   | ZFS dataset for the user (`tank/medforge/workspaces/<user_id>`) |

Environment variables injected at runtime:

```
MEDFORGE_SESSION_ID=<uuid>
MEDFORGE_USER_ID=<uuid>
MEDFORGE_TIER=PUBLIC|PRIVATE
CUDA_VISIBLE_DEVICES=<gpu_idx>
```

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
5. Insert session row: `status='starting'`, chosen `gpu_id`, `slug`, `pack_id`.
6. If insert fails due to `UNIQUE(gpu_id, gpu_active)` conflict, retry a fixed number of times.
7. `COMMIT`

**After commit, spawn container:**

- Name: `mf-session-<slug>`
- Network: `medforge-public-sessions`
- Mount: `/workspace` from user's ZFS dataset
- GPU: `CUDA_VISIBLE_DEVICES` restricted to allocated GPU index

Update session: set `container_id`, `status='running'`, `started_at`. On failure: set `status='error'`, `error_message`. Leaving active status frees the GPU automatically (generated column becomes NULL, unique constraint releases).

#### Stop -- `POST /api/sessions/{id}/stop`

1. Set `status='stopping'`.
2. SIGTERM container, wait up to 30s.
3. Force-kill if still running.
4. Snapshot workspace: `workspace@stop-<unixms>-<slug>`.
5. Set `status='stopped'`, `stopped_at`.

#### Container State Poller (every 30s)

- Query sessions with `status='running'`.
- `docker inspect` container state.
- If not running: set `status='error'`, `stopped_at`, `error_message="container exited unexpectedly"`; emit `session.stop` event with `reason: container_death`.

#### Boot-Time Reconciliation

On medforge-api startup, for sessions in `starting | running | stopping`: if container missing or not running, mark `error` and set `stopped_at`. Prevents stranded GPU locks after restarts.

### Event Logging

One JSON object per line to stdout.

| Event           | Payload                                              |
| --------------- | ---------------------------------------------------- |
| `user.login`    |                                                      |
| `session.start` | `{session_id, user_id, tier, gpu_id, pack_id, slug}` |
| `session.stop`  | `{reason: user \| admin \| container_death}`          |

---

## 5. Storage

ZFS setup script: `@infra/zfs/setup.sh`

### Workspaces

Dataset layout:

```
tank/medforge/workspaces/<user_id>
tank/medforge/system/db
```

All packs run as a fixed non-root UID/GID (1000:1000). On first workspace creation, set dataset mount ownership to that UID/GID. Optional hard quota applied at dataset creation time. No warning system.

### Snapshots

Taken on session stop only: `workspace@stop-<unixms>-<slug>`.

No scheduled snapshots, retention automation, or restore API/UI. Restore is manual admin ZFS ops.

---

## 6. Data Model

### Enums

| Enum          | Values                                                     |
| ------------- | ---------------------------------------------------------- |
| Tier          | `PUBLIC`, `PRIVATE`                                        |
| Role          | `user`, `admin`                                            |
| SessionStatus | `starting`, `running`, `stopping`, `stopped`, `error`      |
| PackTier      | `PUBLIC`, `PRIVATE`, `BOTH`                                |

### Tables

#### users

| Column                  | Type     | Notes     |
| ----------------------- | -------- | --------- |
| id                      | UUID     | PK        |
| email                   | string   | unique    |
| password_hash           | string   |           |
| role                    | Role     |           |
| max_concurrent_sessions | int      | default 1 |
| created_at              | datetime |           |

#### auth_sessions

| Column       | Type     | Notes       |
| ------------ | -------- | ----------- |
| id           | UUID     | PK          |
| user_id      | UUID     | FK -> users |
| token_hash   | string   |             |
| created_at   | datetime |             |
| expires_at   | datetime |             |
| revoked_at   | datetime | nullable    |
| last_seen_at | datetime | nullable    |
| ip           | string   | optional    |
| user_agent   | string   | optional    |

#### packs (single seeded row)

| Column        | Type     | Notes    |
| ------------- | -------- | -------- |
| id            | UUID     | PK       |
| name          | string   |          |
| tier          | PackTier |          |
| image_ref     | string   |          |
| image_digest  | string   |          |
| created_at    | datetime |          |
| deprecated_at | datetime | nullable |

#### gpu_devices (seed rows 0-6, all enabled)

| Column  | Type | Notes     |
| ------- | ---- | --------- |
| id      | int  | PK (0..6) |
| enabled | bool |           |

#### sessions

| Column        | Type          | Notes                           |
| ------------- | ------------- | ------------------------------- |
| id            | UUID          | PK                              |
| user_id       | UUID          | FK -> users                     |
| tier          | Tier          |                                 |
| pack_id       | UUID          | FK -> packs                     |
| status        | SessionStatus |                                 |
| container_id  | string        | nullable                        |
| gpu_id        | int           | FK -> gpu_devices, NOT NULL     |
| slug          | string        | unique, 8-char lowercase base32 |
| workspace_zfs | string        |                                 |
| created_at    | datetime      |                                 |
| started_at    | datetime      | nullable                        |
| stopped_at    | datetime      | nullable                        |
| error_message | string        | nullable                        |

**GPU exclusivity via generated column + unique index:**

```sql
gpu_active = CASE WHEN status IN ('starting', 'running', 'stopping') THEN 1 ELSE NULL END

UNIQUE(gpu_id, gpu_active)
```

Enforces at most one active session per GPU at the DB level.

**Slug generation:** 8-char lowercase base32, no padding. Generate and retry up to 3 times for uniqueness.

---

## 7. Build Gates & Definition of Done

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

**Acceptance:** 7 concurrent sessions succeed; 8th fails "no GPUs available". Per-user limit enforced under concurrent requests. Session stop produces a ZFS snapshot.

### Gate 4 -- Fault Recovery

Container state poller detects dead containers. Boot-time reconciliation frees stranded sessions.

**Acceptance:** Abrupt container kill (`docker kill`) is detected and marked `error` within 30s. API restart reconciles all orphaned sessions back to `error`/`stopped`.

### Gate 5 -- Routing & Isolation

Caddy wildcard route proxies to running sessions (`@infra/caddy/Caddyfile`). East-west isolation enforced (`@infra/firewall/setup.sh`).

**Acceptance:** Owner can access their session; other user gets 403; unauthenticated gets 401. From inside a session, cannot reach another session's :8080. code-server terminal websockets work.

### Gate 6 -- End-to-End

Full user flow through the UI: log in, create a PUBLIC session, land in code-server, run a CUDA program in the terminal, stop the session, verify ZFS snapshot exists.

**Acceptance:** The entire flow completes without manual intervention. GPU is visible inside the session (`nvidia-smi`). Workspace files persist across session restarts. Snapshot is present after stop.

### Definition of Done

- A user can log in, start a PUBLIC GPU session, and access code-server at `s-<slug>.medforge.<domain>`.
- GPU exclusivity is enforced by DB constraint and race-safe allocation.
- Per-user concurrent session limits are enforced.
- Work persists on ZFS and snapshots occur on stop.
- Poller + boot-time reconciliation prevents stranded sessions/GPU locks after failures/restarts.
- PRIVATE exists in enums/policies/networks but session creation returns 501.
