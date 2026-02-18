# MedForge Architecture (Canonical)

### Scope

### In Scope

- system-level runtime architecture and trust boundaries
- validation truth precedence and claim status vocabulary
- high-level contracts across sessions, routing, and competitions
- platform non-goals and runtime status register

### Out of Scope

- endpoint-level deep contracts owned by domain docs (`docs/sessions.md`, `docs/auth-routing.md`, `docs/competitions.md`)
- schema-level entities/enums/invariants owned by runtime code (`apps/api/app/models.py`, `apps/api/alembic/versions/`)

### Canonical Sources

- `deploy/compose/docker-compose.yml`
- `deploy/caddy/Caddyfile`
- `apps/api/app/routers/control_plane.py`
- `apps/api/app/session_lifecycle.py`
- `apps/api/app/session_recovery.py`

## Validation Scope and Truth Sources

Canonical runtime claim precedence:
1. Latest accepted phase evidence in `docs/evidence/<date>/`
2. Validators in `ops/host/validate-phase*.sh` and `ops/host/validate-policy-remote-external.sh`
3. Source contracts in `apps/api`, `apps/web`, `deploy/caddy`, and `deploy/compose`

## Platform Scope

Platform overview:
- MedForge provisions EXTERNAL and INTERNAL GPU-backed browser development sessions (`code-server`) and permanent competitions on a single host.

Primary goals:
- Stable exposure-scoped session lifecycle (create, run, stop, recover) with one physical GPU per active session.
- Permanent EXTERNAL competitions with deterministic scoring/leaderboard behavior.
- Wildcard owner-bound session routing and isolated per-session workspaces with stop snapshots.

Constraints:
- Single-host deployment target.
- Stack: Next.js (`apps/web`), FastAPI + SQLModel (`apps/api`), MariaDB, Caddy, Docker, ZFS.
- INTERNAL exposure is runtime-enabled behind explicit user entitlement (`can_use_internal`).

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
- Allocation model: one physical GPU per active session.
- Workspace model: one per-session ZFS dataset mounted into each runtime.

Dev overlay: `deploy/compose/docker-compose.dev.yml` adds `medforge-web-dev` (hot-reload Next.js on `dev.medforge.<domain>`), routed by Caddy but not present in the production compose file.

Source manifests: `deploy/compose/docker-compose.yml`, `deploy/caddy/Caddyfile`, `deploy/packs/default/Dockerfile`, `deploy/compose/.env.example`.

## Network and Routing Architecture

| Network | Purpose |
| --- | --- |
| `medforge-control` | Control-plane traffic (`web <-> api <-> db <-> caddy`) |
| `medforge-external-sessions` | EXTERNAL runtime session containers |
| `medforge-internal-sessions` | INTERNAL runtime session containers (no internet egress) |

Fixed IP contract on `medforge-external-sessions`: `medforge-caddy=172.30.0.2`, `medforge-api=172.30.0.3`.

| Hostname | Routed Service |
| --- | --- |
| `medforge.<domain>` | `medforge-web` |
| `external.medforge.<domain>` | `medforge-web` (EXTERNAL surface) |
| `internal.medforge.<domain>` | `medforge-web` (INTERNAL surface) |
| `api.medforge.<domain>` | `medforge-api` |
| `s-<slug>.external.medforge.<domain>` | EXTERNAL session upstream |
| `s-<slug>.internal.medforge.<domain>` | INTERNAL session upstream |
| `dev.medforge.<domain>` | `medforge-web-dev` (dev overlay, hot-reload) |

Routing invariants:
- Caddy strips client `X-Upstream`; client hints cannot select session upstreams.
- Upstream selection comes only from API `GET /api/v2/auth/session-proxy`.
- Missing API-supplied upstream fails closed (`502`).
- External wildcard `.../api/v2/auth/session-proxy` is blocked (`403`).
- Wildcard root matrix: `401` unauthenticated, `403` non-owner, `200` owner/admin for running session; after async stop finalization -> `404`.

Reality gate for external claims:
- `DOMAIN` must be consistent across Compose/API/web config.
- External DNS must resolve `medforge.<domain>`, `external.medforge.<domain>`, `internal.medforge.<domain>`, `api.medforge.<domain>`.
- TLS hostname validation must pass for `medforge.<domain>` and `api.medforge.<domain>`.

## API Surface Overview

| Route Prefix | Domain | Detail Doc |
| --- | --- | --- |
| `/api/v2/auth/*` | Authentication (shared) | `docs/auth-routing.md` |
| `/api/v2/me` | Identity (shared) | `docs/auth-routing.md` |
| `/api/v2/external/sessions/*` | EXTERNAL sessions | `docs/sessions.md` |
| `/api/v2/internal/sessions/*` | INTERNAL sessions | `docs/sessions.md` |
| `/api/v2/external/competitions/*` | EXTERNAL competitions | `docs/competitions.md` |
| `/api/v2/internal/competitions/*` | INTERNAL competitions | `docs/competitions.md` |
| `/api/v2/external/datasets/*` | EXTERNAL datasets | `docs/competitions.md` |
| `/api/v2/internal/datasets/*` | INTERNAL datasets | `docs/competitions.md` |
| `/api/v2/external/admin/*` | EXTERNAL admin | `docs/competitions.md` |
| `/api/v2/internal/admin/*` | INTERNAL admin | `docs/competitions.md` |
| `/healthz` | Health check | `docs/sessions.md` |

## API Response Contract

This is the single authoritative definition of the API envelope format. Other docs cross-reference this section.

Success responses use a universal envelope:
- `{ "data": ..., "meta": { "request_id": ..., "api_version": ..., "timestamp": ..., ... } }`

Error responses use RFC 7807-style `application/problem+json` payloads:
- `{ "type": ..., "title": ..., "status": ..., "detail": ..., "instance": ..., "code": ..., "request_id": ..., "errors": [...] }`
- `errors` is optional and used for validation-style failures.

Client parsing strategy: use `detail` when present, fall back to `title`, then fall back to a generic status message.

## Session Runtime Summary

Session lifecycle covers create, stop, recovery, and health. State model: active = `starting|running|stopping`; terminal = `stopped|error`. INTERNAL routes require `can_use_internal=true`.

Full contract: `docs/sessions.md`.

## Competition Architecture Summary

Four seeded permanent competitions: `titanic-survival`, `rsna-pneumonia-detection`, `cifar-100-classification`, `oxford-pet-segmentation`. Scoring mode: `single_realtime_hidden`. Leaderboard rule: `best_per_user` with deterministic ordering. Daily submission caps enforced per user per competition.

Full contract: `docs/competitions.md`.

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
- Competition data uses three disjoint roots: `TRAINING_DATA_ROOT` (training), `PUBLIC_EVAL_DATA_ROOT` (public eval + manifest), and `TEST_HOLDOUTS_DIR` (hidden labels only).
- Session containers never mount `TEST_HOLDOUTS_DIR`; hidden holdouts remain API/worker-only.

Operational detail references: `docs/runbook.md`, `ops/storage/zfs-setup.sh`, `ops/network/firewall-setup.sh`, `ops/host/bootstrap-easy.sh`.
