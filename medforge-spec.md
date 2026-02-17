# MedForge Platform Specification

> Runtime-truth specification for MedForge.
> Validation policy is **remote-public only** (validation lane), while session tiering remains `PUBLIC`/`PRIVATE` in API models.
> As of `2026-02-17T06:48:56Z` (latest canonical Phase 5 PASS artifact).

---

## 0. Source-of-Truth Policy

This file is the top-level contract for what MedForge does today.

- `VERIFIED`: behavior is backed by current runtime evidence and executable phase checks.
- `UNVERIFIED`: behavior exists in code/docs but is not currently backed by accepted canonical evidence.
- `NOT_IMPLEMENTED`: behavior is intentionally modeled but blocked at runtime.

Claim precedence:

1. Latest canonical phase evidence in `docs/evidence/<date>/`.
2. Executable validators under `ops/host/validate-phase*.sh` and `ops/host/validate-policy-remote-public.sh`.
3. Current source contracts (`apps/api`, `apps/web`, `deploy/caddy`, `deploy/compose`).

If these disagree, runtime evidence is authoritative until rerun evidence supersedes it.

---

## 1. Hard Status (VERIFIED)

Canonical validation mode: **remote-public only**.

| Phase | Outcome | Canonical Artifact | Timestamp (UTC) | Status |
| --- | --- | --- | --- | --- |
| 0 | Host foundation (GPU, ZFS, DNS, TLS) | `docs/evidence/2026-02-17/phase0-host-20260217T064618Z.md` | `2026-02-17T06:46:18Z` | PASS |
| 1 | Compose/bootstrap/seed readiness | `docs/evidence/2026-02-17/phase1-bootstrap-20260217T064621Z.md` | `2026-02-17T06:46:21Z` | PASS |
| 2 | Auth + session API contracts | `docs/evidence/2026-02-17/phase2-auth-api-20260217T064639Z.md` | `2026-02-17T06:46:39Z` | PASS |
| 3 | Session lifecycle + recovery | `docs/evidence/2026-02-17/phase3-lifecycle-recovery-20260217T064705Z.md` | `2026-02-17T06:47:05Z` | PASS |
| 4 | Routing/isolation/end-to-end/browser lane | `docs/evidence/2026-02-17/phase4-routing-e2e-20260217T064739Z.md` | `2026-02-17T06:47:39Z` | PASS |
| 5 | Competition platform/scoring/leaderboards | `docs/evidence/2026-02-17/phase5-competitions-20260217T064856Z.md` | `2026-02-17T06:48:56Z` | PASS |

Status freshness rules:

- Status is **stale** when platform-affecting contracts change without a new accepted phase run.
- Platform-affecting contracts include:
  - `apps/api/app/routers/*`, `apps/api/app/session_*`, `apps/api/app/deps.py`, `apps/api/app/config.py`
  - `deploy/caddy/Caddyfile`
  - `deploy/compose/docker-compose.yml` and `deploy/compose/.env` policy values
  - `ops/host/validate-phase*.sh` and `ops/host/lib/remote-public.sh`
- When stale, this document may still describe intent, but no new runtime claim should be treated as `VERIFIED` until revalidated.

---

## 2. Platform Overview

MedForge provisions GPU-backed browser development sessions (`code-server`) on a single multi-GPU Ubuntu host. Sessions run from a default immutable pack image (digest pinned) and use isolated per-session ZFS workspaces with snapshot-on-stop rollback points.

Implementation snapshot:

- Competition APIs/UI and scoring are implemented.
- Cookie auth foundation and `/api/v1/me` are implemented.
- PUBLIC session create/stop and recovery reconciliation are implemented.
- Canonical runtime progression and evidence policy are defined in `@docs/phase-checking-strategy.md`.

### 2.1 Goals

- Launch stable PUBLIC sessions with browser IDE, terminal, and GPU access.
- Run permanent PUBLIC competitions with scoring and leaderboards:
  - `titanic-survival`
  - `rsna-pneumonia-detection`
  - `cifar-100-classification`
- Enforce one physical GPU per active session.
- Support up to seven concurrent active sessions on this host when all seeded GPUs are enabled.
- Enforce per-user concurrent session limits.
- Route session access by wildcard host `s-<slug>.medforge.<domain>`.
- Persist per-session ZFS workspaces and create stop snapshots.
- Emit structured lifecycle logs to stdout with context IDs (`session_id`, `user_id`, `slug`).

### 2.2 Constraints

- Single-host deployment target (Ubuntu 24.04 LTS class environment).
- Stack:
  - Next.js + TypeScript (`apps/web`)
  - FastAPI + SQLModel (`apps/api`)
  - MariaDB
- `code-server` is the browser IDE runtime.
- Competition scoring uses hidden holdout evaluation with:
  - `scoring_mode=single_realtime_hidden`
  - `leaderboard_rule=best_per_user`
  - no alpha-finals stage
- PRIVATE tier is represented in models/policy surfaces, but runtime create for `tier=private` returns `501`.

### 2.3 Non-Goals

- Forums and marketplace features.
- Managed read-only dataset mounts into session containers (dataset catalog exists).
- Exfiltration prevention against screenshots/copying.
- Enterprise identity integrations (SSO/SCIM).
- Multi-node scheduling/orchestration.
- Lease TTL/heartbeat session renewal model (current model is explicit stop + polling + boot reconciliation).
- Scheduled snapshot retention automation.
- Snapshot restore API/UI (manual admin ZFS operations only).
- Advanced observability stack beyond structured logs and host tools.

---

## 3. Reality Gate (Must Pass Before "It Works" Claims)

The platform can pass unit/integration checks and still fail real usage if deployment preconditions are missing. The following are hard prerequisites.

### 3.1 DNS and Domain Preconditions (VERIFIED requirement)

- `DOMAIN` must be set and used consistently across compose, API, and web.
- Public DNS must resolve:
  - `medforge.<DOMAIN>`
  - `api.medforge.<DOMAIN>`
  - `s-<slug>.medforge.<DOMAIN>`
- Wildcard DNS must be routable before Phase 4/real browser claims are valid.

### 3.2 TLS Preconditions (VERIFIED requirement)

- Valid certificate chain and hostname verification for:
  - `medforge.<DOMAIN>`
  - `api.medforge.<DOMAIN>`
- No insecure bypass is allowed for canonical validation.

### 3.3 Compose and Env Preconditions (VERIFIED requirement)

Required env/config posture:

- `PACK_IMAGE` is digest pinned (`image@sha256:...`).
- `NEXT_PUBLIC_API_URL` targets `https://api.medforge.<DOMAIN>`.
- Cookie scope and domain are coherent (`COOKIE_DOMAIN=.medforge.<DOMAIN>`).
- `PUBLIC_SESSIONS_NETWORK` exists and is reachable by API and Caddy.

### 3.4 Host Runtime Preconditions (VERIFIED requirement)

- `medforge-api` mounts:
  - `/var/run/docker.sock`
  - `/tank:/tank` with shared propagation
- ZFS is available on host (`/dev/zfs`, `zfs` CLI), and docker runtime has required privileges.
- `medforge-public-sessions` fixed IP contract:
  - `medforge-caddy=172.30.0.2`
  - `medforge-api=172.30.0.3`

### 3.5 Failure Mapping (Operational Contract)

- `ERR_NAME_NOT_RESOLVED` or "server IP not found" for `medforge.<DOMAIN>`: DNS is not configured or not propagated.
- `POST /api/v1/auth/signup failed: 404` in web UI: browser is calling the wrong API base URL or API host routing is broken.
- `Failed to start session runtime.` during session create: runtime mount/permission/ZFS/container-start prerequisites are not satisfied.

---

## 4. As-Built Architecture Contract (VERIFIED)

### 4.1 Control Plane

| Component | Role |
| --- | --- |
| `medforge-web` | Next.js frontend |
| `medforge-api` | FastAPI control plane (auth, sessions, competitions) |
| `medforge-api-worker` | Submission scoring worker |
| `medforge-db` (MariaDB) | Persistent system of record |
| `medforge-caddy` | TLS termination + wildcard routing + auth boundary |

### 4.2 Data Plane

- Session runtime: one container per session (`mf-session-<slug>`).
- Runtime IDE: `code-server --auth none`; Caddy/API is the security boundary.
- One physical GPU allocated per active session.
- Session workspace: per-session ZFS dataset mount.

### 4.3 Network Model

- `medforge-control`: web/api/db/control-plane traffic.
- `medforge-public-sessions`: PUBLIC session containers.
- `medforge-private-sessions`: placeholder only.
- East-west rule: only Caddy fixed IP may reach session `:8080`.

### 4.4 Storage Model

Dataset layout:

```text
tank/medforge/workspaces/<user_id>
tank/medforge/workspaces/<user_id>/<session_id>
tank/medforge/system/db
```

Snapshot naming:

```text
<workspace_zfs>@stop-<unixms>
```

---

## 5. Public HTTP Contract (As-Built)

Common API behavior:

- Canonical prefix: `/api/v1`.
- Success responses: envelope `{data, meta}`.
- Error responses: `application/problem+json` including `type`, `status`, `detail`, `code`, `request_id`.

### 5.1 Auth and Identity Endpoints (VERIFIED)

| Endpoint | Behavior |
| --- | --- |
| `POST /api/v1/auth/signup` | Creates account + auth cookie, returns `201`; enforces origin policy + auth rate limit |
| `POST /api/v1/auth/login` | Issues auth cookie, returns `200`; enforces origin policy + auth rate limit |
| `POST /api/v1/auth/logout` | Revokes active auth session token when present, returns `200`; enforces origin policy |
| `GET /api/v1/me` | Authenticated principal identity; unauthenticated returns `401` |

Auth model:

- HTTP-only cookie session backed by DB token hash.
- Idle TTL + max TTL enforced.
- Legacy header identity fallback is removed from request auth flow.

### 5.2 Session Control Endpoints (VERIFIED)

| Endpoint | Behavior |
| --- | --- |
| `GET /api/v1/sessions/current` | Returns newest active (`starting|running|stopping`) session for caller, else `null` |
| `POST /api/v1/sessions` | Creates PUBLIC session (`201`) or returns `501` for `tier=private`; origin-guarded |
| `POST /api/v1/sessions/{id}/stop` | Intent-based async stop (`202`) for running/starting/stopping/terminal; origin-guarded |

### 5.3 Internal Session-Proxy Contract (VERIFIED)

Endpoint: `GET /api/v1/auth/session-proxy` on API host, used by Caddy `forward_auth`.

With `Host: s-<slug>.medforge.<DOMAIN>`:

- `200` owner/admin + running session; API sets `X-Upstream: mf-session-<slug>:8080`.
- `401` unauthenticated.
- `403` authenticated but not owner/admin.
- `404` bad host/slug/session/not-running.

### 5.4 External Wildcard Contract (VERIFIED)

- `https://s-<slug>.medforge.<DOMAIN>/api/v1/auth/session-proxy` is intentionally blocked with `403`.
- Real user reachability contract is wildcard root:
  - `401` unauthenticated
  - `403` authenticated non-owner
  - `200` authenticated owner for running session
- After async stop finalization completes, wildcard root returns `404`.

### 5.5 Competition Endpoints (VERIFIED)

Public read routes:

- `GET /api/v1/competitions`
- `GET /api/v1/competitions/{slug}`
- `GET /api/v1/competitions/{slug}/leaderboard`
- `GET /api/v1/datasets`
- `GET /api/v1/datasets/{slug}`

Submission/admin routes:

- `POST /api/v1/competitions/{slug}/submissions` (auth + origin guard, file validation, cap enforcement, optional auto-score).
- `GET /api/v1/competitions/{slug}/submissions/me` (auth required).
- `POST /api/v1/admin/submissions/{submission_id}/score` (admin + origin guard).

Seeded permanent PUBLIC competitions:

- `titanic-survival`
- `rsna-pneumonia-detection`
- `cifar-100-classification`

Competition behavior guarantees:

- Valid submissions can be scored to a non-null official `primary_score`.
- Daily submission cap is enforced per user per competition.
- Leaderboard ranking is deterministic from official scored rows.

---

## 6. Session Lifecycle and Recovery Contract (VERIFIED)

Create flow (`POST /api/v1/sessions`):

1. Reject `tier=private` with `501` (`NOT_IMPLEMENTED` path).
2. Resolve user and pack compatibility.
3. In transaction: lock user, enforce per-user active limit, lock/select free enabled GPU, insert `starting` session row.
4. Provision workspace dataset (`uid:gid 1000:1000`, optional quota).
5. Start runtime container with one physical GPU and canonical env (`MEDFORGE_*`, `NVIDIA_VISIBLE_DEVICES`, `CUDA_VISIBLE_DEVICES=0`).
6. Finalize to `running` or `error`.

Stop flow (`POST /api/v1/sessions/{id}/stop`):

- `starting|running` -> mark `stopping`, return `202`.
- `stopping` -> return `202` (idempotent).
- `stopped|error` -> return `202` with terminal message.
- Stop/snapshot finalization happens asynchronously in recovery.

Recovery flow:

- Poller reconciles `starting|running|stopping` states.
- Startup reconciliation runs on API boot.
- Poll loop failures use exponential backoff capped by `SESSION_POLL_BACKOFF_MAX_SECONDS`.
- `/healthz` returns:
  - `200` + `ok` when API/recovery healthy
  - `503` + `degraded` when recovery is enabled but unavailable

State invariants:

- Active statuses: `starting`, `running`, `stopping`.
- Terminal statuses: `stopped`, `error`.
- GPU exclusivity: DB enforced by generated `gpu_active` + unique `(gpu_id, gpu_active)`.

---

## 7. Security and Isolation Contract (VERIFIED)

- Client-supplied `X-Upstream` is stripped by Caddy.
- Upstream selection comes only from API-issued `X-Upstream` in internal session-proxy response.
- Missing API-supplied upstream on wildcard route fails closed with `502`.
- Wildcard internal auth path is blocked externally (`403`).
- State-changing endpoints apply origin allowlist checks for MedForge domain hosts.
- Session-to-session direct access on `:8080` is blocked by firewall policy.

---

## 8. Gap Register

`NOT_IMPLEMENTED`:

- `tier=private` runtime path returns `501` by design.
- Private-network enforcement model exists structurally, but no private session runtime implementation is active.

`UNVERIFIED` unless separately evidenced after latest canonical run:

- Any claim requiring new host topology beyond single-host deployment.
- Any claim requiring automated restore UX/snapshot retention workflows.
- Any claim tied to changed env/domain/routing/runtime settings without new phase evidence.

---

## 9. Validation Workflow Contract

Canonical commands:

```bash
bash ops/host/validate-policy-remote-public.sh
bash ops/host/validate-phases-all.sh
```

Phase-specific reruns:

```bash
bash ops/host/validate-phase0-host.sh
bash ops/host/validate-phase1-bootstrap.sh
bash ops/host/validate-phase2-auth-api.sh
bash ops/host/validate-phase3-lifecycle-recovery.sh
bash ops/host/validate-phase4-routing-e2e.sh
bash ops/host/validate-phase5-competitions.sh
```

Evidence update discipline:

- Each accepted phase run must produce `.md` + `.log` artifacts.
- `docs/phase-checking-strategy.md` and `docs/validation-logs.md` must be updated in the same change set.
- Existing evidence files are immutable once accepted.

---

## 10. Detailed References

- `@docs/architecture.md`
- `@docs/sessions.md`
- `@docs/auth-routing.md`
- `@docs/data-model.md`
- `@docs/phase-checking-strategy.md`
- `@docs/validation-logs.md`
- `@docs/runbook.md`
