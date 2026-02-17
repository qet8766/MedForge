# MedForge Architecture (Canonical)

Implementation status note (2026-02-17):
- Canonical validation lane is `remote-public` only.
- Latest full progression is `PASS` through Phase 5 (`docs/phase-checking-strategy.md`, `docs/validation-logs.md`).
- This file is architecture/runtime contract only; operations runbooks stay in `docs/runbook.md`.

## Validation Scope and Truth Sources

Canonical runtime claim precedence:
1. Latest accepted phase evidence in `docs/evidence/<date>/`
2. Validators in `ops/host/validate-phase*.sh` and `ops/host/validate-policy-remote-public.sh`
3. Source contracts in `apps/api`, `apps/web`, `deploy/caddy`, and `deploy/compose`

Status vocabulary: `VERIFIED` (evidenced), `UNVERIFIED` (described but not evidenced), `NOT_IMPLEMENTED` (modeled but runtime-blocked).

Runtime claims become stale until revalidated when these change:
`apps/api/app/routers/*`, `apps/api/app/session_*`, `apps/api/app/deps.py`, `apps/api/app/config.py`, `deploy/caddy/Caddyfile`, `deploy/compose/docker-compose.yml`, `deploy/compose/.env` policy values, `ops/host/validate-phase*.sh`, `ops/host/lib/remote-public.sh`.

## Platform Scope

Platform overview:
- MedForge provisions PUBLIC GPU-backed browser development sessions (`code-server`) and permanent PUBLIC competitions on a single host.

Primary goals:
- Stable PUBLIC session lifecycle (create, run, stop, recover) with one physical GPU per active session.
- Permanent PUBLIC competitions with deterministic scoring/leaderboard behavior.
- Wildcard owner-bound session routing and isolated per-session workspaces with stop snapshots.

Constraints:
- Single-host deployment target.
- Stack: Next.js (`apps/web`), FastAPI + SQLModel (`apps/api`), MariaDB, Caddy, Docker, ZFS.
- PRIVATE tier remains modeled in policy/data surfaces; runtime create for `tier=private` returns `501`.

Non-goals:
- Multi-node scheduling/orchestration.
- Snapshot restore API/UI and scheduled snapshot retention automation.
- Enterprise SSO/SCIM integrations and marketplace/forum features.

## System Topology

### Control Plane
| Component | Runtime Role |
| --- | --- |
| `medforge-web` | Next.js frontend for auth, sessions, competitions, datasets |
| `medforge-api` | FastAPI control plane for auth/session/competition APIs |
| `medforge-api-worker` | Background submission scoring worker |
| `medforge-db` | MariaDB system of record |
| `medforge-caddy` | TLS termination, wildcard routing, auth boundary |

### Data Plane
- Runtime containers: `mf-session-<slug>` (one per active session).
- Runtime IDE: `code-server --auth none`.
- Allocation model: one physical GPU per active PUBLIC session.
- Workspace model: one per-session ZFS dataset mounted into each runtime.

Source manifests: `deploy/compose/docker-compose.yml`, `deploy/caddy/Caddyfile`, `deploy/packs/default/Dockerfile`, `deploy/compose/.env.example`.

## Network and Routing Architecture

| Network | Purpose |
| --- | --- |
| `medforge-control` | Control-plane traffic (`web <-> api <-> db <-> caddy`) |
| `medforge-public-sessions` | PUBLIC runtime session containers |
| `medforge-private-sessions` | PRIVATE-tier placeholder only |

Fixed IP contract on `medforge-public-sessions`: `medforge-caddy=172.30.0.2`, `medforge-api=172.30.0.3`.

| Hostname | Routed Service |
| --- | --- |
| `medforge.<domain>` | `medforge-web` |
| `api.medforge.<domain>` | `medforge-api` |
| `s-<slug>.medforge.<domain>` | `mf-session-<slug>:8080` via API-authorized upstream |

Routing invariants:
- Caddy strips client `X-Upstream`; client hints cannot select session upstreams.
- Upstream selection comes only from API `GET /api/v1/auth/session-proxy`.
- Missing API-supplied upstream fails closed (`502`).
- External wildcard `.../api/v1/auth/session-proxy` is blocked (`403`).
- Wildcard root matrix: `401` unauthenticated, `403` non-owner, `200` owner/admin for running session; after async stop finalization -> `404`.

Reality gate for public claims:
- `DOMAIN` must be consistent across Compose/API/web config.
- Public DNS must resolve `medforge.<domain>`, `api.medforge.<domain>`, `s-<slug>.medforge.<domain>`.
- TLS hostname validation must pass for `medforge.<domain>` and `api.medforge.<domain>`.

## Session Runtime Contract

API prefix: `/api/v1`.

Endpoint set:
- Session control: `GET /api/v1/sessions/current`, `POST /api/v1/sessions`, `POST /api/v1/sessions/{id}/stop`.
- Routing auth: `GET /api/v1/auth/session-proxy`.
- Health: `GET /healthz`.

State model: active = `starting|running|stopping`; terminal = `stopped|error`.

Runtime invariants:
- Allocation is transactional: lock user row, enforce per-user concurrency, choose enabled free GPU, insert `starting` row.
- GPU exclusivity is enforced by allocation-time locking plus active-state checks.
- Stop requests are intent-based (`202`); stop/snapshot finalization is asynchronous in recovery.
- Recovery runs on startup and poll loop, using exponential backoff capped by `SESSION_POLL_BACKOFF_MAX_SECONDS`.
- Health contract: `200` + `ok` when recovery is healthy; `503` + `degraded` when enabled recovery is unavailable.
- `POST /api/v1/sessions` with `tier=private` returns `501` (`NOT_IMPLEMENTED`).

API response contract:
- Success: envelope `{data, meta}`.
- Errors: `application/problem+json` including `type`, `status`, `detail`, `code`, `request_id`.

## Security Boundaries

- Session runtime keeps `code-server --auth none`; Caddy + API enforce access control.
- API-issued upstream headers are authoritative; client-supplied upstream headers are stripped.
- Wildcard internal auth path is blocked externally (`403`).
- State-changing endpoints enforce MedForge-domain origin allowlist checks.
- East-west policy allows only Caddy fixed IP to reach session `:8080`.

## Data and Persistence Boundaries

Persistent layout:
```
tank/medforge/workspaces/<user_id>
tank/medforge/workspaces/<user_id>/<session_id>
tank/medforge/system/db
```

Storage/runtime guarantees:
- Each session mounts only its own workspace dataset.
- Workspace dataset ownership is `uid:gid 1000:1000`.
- Optional quota can be applied at dataset creation.
- Stop snapshots use `<workspace_zfs>@stop-<unixms>`.
- `PACK_IMAGE` is digest-pinned (`image@sha256:...`).

Out of scope: scheduled snapshot retention automation; snapshot restore API/UI (manual admin ZFS operations only).

Operational detail references: `docs/runbook.md`, `ops/storage/zfs-setup.sh`, `ops/network/firewall-setup.sh`, `ops/host/bootstrap-easy.sh`.

## Competition Architecture

Seeded permanent PUBLIC competitions: `titanic-survival`, `rsna-pneumonia-detection`, `cifar-100-classification`.

Competition posture: `scoring_mode=single_realtime_hidden`, `leaderboard_rule=best_per_user`, `evaluation_policy=canonical_test_first`, no alpha-finals stage.

Competition endpoints:
- Read: `GET /api/v1/competitions`, `GET /api/v1/competitions/{slug}`, `GET /api/v1/competitions/{slug}/leaderboard`, `GET /api/v1/datasets`, `GET /api/v1/datasets/{slug}`.
- Write/admin: `POST /api/v1/competitions/{slug}/submissions`, `GET /api/v1/competitions/{slug}/submissions/me`, `POST /api/v1/admin/submissions/{submission_id}/score`.

Competition invariants:
- Valid submissions can produce non-null official `primary_score`.
- Daily submission caps are enforced per user per competition.
- Leaderboard ranking is deterministic from official scored rows.

## Runtime Claim Status Register

| Claim | Status | Notes |
| --- | --- | --- |
| PRIVATE tier runtime create path (`tier=private`) | `NOT_IMPLEMENTED` | Runtime returns `501` by design. |
| Private-network session runtime enforcement | `NOT_IMPLEMENTED` | Model exists structurally; no active private runtime path. |
| Multi-host scheduling/orchestration claims | `UNVERIFIED` | Canonical evidence scope is single-host. |
| Automated snapshot retention workflows | `NOT_IMPLEMENTED` | Not part of current runtime behavior. |
| Snapshot restore API/UI | `NOT_IMPLEMENTED` | Manual admin ZFS restore only. |

## Reference Map

- `docs/phase-checking-strategy.md`
- `docs/validation-logs.md`
- `docs/sessions.md`
- `docs/auth-routing.md`
- `docs/competitions.md`
- `docs/data-model.md`
- `docs/runbook.md`
- `deploy/compose/docker-compose.yml`
- `deploy/caddy/Caddyfile`
- `apps/api/app/routers/control_plane.py`
- `apps/api/app/session_lifecycle.py`
- `apps/api/app/session_recovery.py`
