# MedForge Platform Specification

> PUBLIC-first. PRIVATE is fully represented in the data model and policy surface, but `tier=PRIVATE` session creation returns **501 Not Available**.
> Single Ubuntu host with **7x RTX 5090**. Browser IDE = **code-server**.

This file is the big-picture source of truth. Detailed docs are split below, but core strategy and delivery intent are intentionally repeated here.

---

## Status Snapshot (2026-02-16)

- Implemented in this repo now:
  - Competition catalog/submission/leaderboard APIs and web pages.
  - Scoring worker + optional auto-score-on-submit path.
  - Gate 2 auth foundations: `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, and `GET /api/me`.
  - Session proxy authorization contract (`GET /api/auth/session-proxy`) for owner/admin on running session rows.
  - Gate 3 alpha lifecycle for PUBLIC: `POST /api/sessions` and `POST /api/sessions/{id}/stop`.
  - Gate 4 recovery paths: startup reconciliation + periodic poller for active session/container drift.
  - Host evidence pass for Gate 5/6 checks (auth matrix, spoof resistance, east-west block, GPU visibility, workspace write, snapshot-on-stop, wildcard browser routing, websocket activity).

---

## 0. Current Machine Specs (Captured 2026-02-15 15:20:42 UTC)

| Area | Current Host |
| --- | --- |
| Hostname | `user-System-Product-Name` |
| OS | Ubuntu `24.04.4 LTS` |
| Kernel | `6.8.0-100-generic` |
| CPU | AMD Ryzen Threadripper PRO 9985WX, `64` cores / `128` threads, max `5.475 GHz` |
| Memory | `503 GiB` RAM, `2.0 GiB` swap |
| GPU | `7 x NVIDIA GeForce RTX 5090` |
| GPU VRAM | `32607 MiB` per GPU |
| NVIDIA driver | `590.48.01` |
| CUDA version | `13.1` |
| Project filesystem | `/home/shk/projects/MedForge` on `ext4` (`/dev/nvme2n1p2`), `7.3T` total (`50G` used) |

Implementation note:

- The platform spec targets ZFS for workspace datasets and snapshots.
- The MedForge repo currently lives on `ext4`; ZFS pool/datasets should be verified/provisioned during Gate 0 for runtime workspace storage.
- `/data` exists on this host but is not part of the current MedForge pathing/spec.

---

## 1. Executive Summary

MedForge is a single-host GPU development platform that gives each user browser-based VS Code sessions (`code-server`) with terminal + CUDA access.

Target product posture:

- PUBLIC tier is available now.
- PRIVATE tier is represented in models/policies but blocked at runtime with `501`.
- One default immutable Pack (image digest pinned) is used to avoid drift.
- Every session gets exactly one GPU and its own ZFS workspace dataset.
- Session routing is wildcard-subdomain based: `s-<slug>.medforge.<domain>`.

---

## 2. Product Direction

### Goals

- Launch stable PUBLIC GPU sessions end-to-end.
- Launch permanent Kaggle-style mock competitions and leaderboards for PUBLIC data tracks.
- Enforce strict GPU exclusivity (1 active session per physical GPU).
- Enforce per-user concurrent session limits under concurrency.
- Persist workspace data on ZFS with snapshot-on-stop rollback points.
- Keep auth/routing centralized through Caddy + API authorization checks.
- Keep operations simple enough for a single Ubuntu host.

### Non-Goals (current scope)

- Multi-node scheduling and cluster orchestration.
- PRIVATE controls implementation (egress blocking, strict auditing, transfer controls).
- Enterprise auth (SSO/SCIM).
- Public dataset redistribution beyond internal/private mirrored competition data.
- Restore API/UI and automated snapshot retention.
- Advanced observability stack beyond structured app logs + host tools.

Detailed doc:

- `@docs/overview.md`

---

## 3. Architecture Snapshot

### Control Plane

| Component | Role |
| --- | --- |
| `medforge-web` | Next.js frontend |
| `medforge-api` | FastAPI + session manager |
| `MariaDB` | System of record |
| `Caddy` | TLS termination, wildcard routing, auth gateway |

### Data Plane

- One Docker container per session (`mf-session-<slug>`).
- `code-server` runs with `--auth none`; Caddy/API is the access gate.
- Session workspace mount is per-session ZFS dataset, not shared across sessions.

### Network and Access Model

- `medforge-control`: web/api/db traffic.
- `medforge-public-sessions`: PUBLIC session containers.
- `medforge-private-sessions`: placeholder network.
- Caddy joins control + public sessions networks.
- Firewall rules allow only Caddy fixed IP (`172.30.0.2`) to reach session `:8080`.

### Storage Model

- ZFS datasets:
```
tank/medforge/workspaces/<user_id>
tank/medforge/workspaces/<user_id>/<session_id>
tank/medforge/system/db
```
- Snapshot format on stop: `<workspace_zfs>@stop-<unixms>`.

Detailed doc:

- `@docs/architecture.md`

---

## 4. Session Lifecycle Snapshot

### Create (`POST /api/sessions`)

- Validate auth and input (`tier`, optional `pack_id`).
- Reject `tier=PRIVATE` with `501`.
- In one transaction:
1. lock user row (`FOR UPDATE`)
2. enforce per-user active-session limit
3. select and lock a free enabled GPU
4. insert session in `starting` with `gpu_id`, `slug`, and `workspace_zfs`
- After commit:
1. ensure session dataset exists and is owned by `1000:1000`
2. start container on `medforge-public-sessions`
3. bind exactly one physical GPU at Docker runtime
4. set runtime env (`MEDFORGE_SESSION_ID`, `MEDFORGE_USER_ID`, `MEDFORGE_TIER`, `MEDFORGE_GPU_ID`, `NVIDIA_VISIBLE_DEVICES`, `CUDA_VISIBLE_DEVICES=0`)
5. finalize as `running` or terminal `error`.

### Stop (`POST /api/sessions/{id}/stop`)

- Transition to `stopping`.
- Graceful terminate, then force-kill if required.
- Snapshot session dataset.
- Finalize `stopped` on success or `error` on snapshot failure.
- Endpoint is idempotent for repeated calls.

### Recovery

- Poller every 30s reconciles `starting` and `running` sessions against actual container state.
- Boot-time reconciliation processes `starting | running | stopping` sessions and forces terminal consistency.
- No session should remain stranded in `starting` or `stopping` after reconciliation.

### State Invariants

- Active states: `starting`, `running`, `stopping`.
- Terminal states: `stopped`, `error`.
- GPU exclusivity enforced in DB via generated `gpu_active` and `UNIQUE(gpu_id, gpu_active)`.

Detailed docs:

- `@docs/sessions.md`
- `@docs/data-model.md`

---

## 5. Security and Routing Snapshot

- Auth is HTTP-only cookie session with DB-stored token hash.
- Cookie scope: subdomain-wide for `*.medforge.<domain>`.
- State-changing endpoints enforce Origin checks.
- Wildcard session routing uses `GET /api/auth/session-proxy`.
- API returns upstream only for authenticated owner/admin when session is running.
- Client-provided upstream hints are never trusted.
- Session-to-session direct access to `:8080` is blocked by firewall policy.

Detailed doc:

- `@docs/auth-routing.md`

---

## 6. Delivery Plan

### Build Gates

| Gate | Outcome |
| --- | --- |
| Gate 0 | Host foundation: Docker/NVIDIA/ZFS/DNS/TLS ready |
| Gate 1 | Compose and DB bootstrap complete |
| Gate 2 | Auth and forward-auth contract complete |
| Gate 3 | Session lifecycle (`create`, `stop`, snapshots) complete |
| Gate 4 | Fault recovery (`poller`, `boot reconcile`) complete |
| Gate 5 | Wildcard routing + east-west isolation complete |
| Gate 6 | End-to-end user flow complete |
| Gate 7 | Permanent competition portal + scoring complete |

### Phased Execution

- Phase 1 (MVP through Gate 7): issues `MF-001` to `MF-019`, estimated `24.0d`.
- Phase 2 (hardening): issues `MF-101` to `MF-105`, estimated `7.0d`.

### Critical Exit Criteria

- Users can log in and reach their own running session at `s-<slug>.medforge.<domain>`.
- 7/7 GPU allocation works with strict exclusivity, no over-allocation.
- Per-user concurrency limits hold under concurrent requests.
- Each session has unique `workspace_zfs`; snapshots are created on stop.
- Recovery paths prevent stranded active rows and stranded GPU locks.
- Permanent PUBLIC competitions are available with hidden-holdout `leaderboard_score` and enforced daily submission caps.

Detailed docs:

- `@docs/build-gates.md`
- `@docs/implementation-checklist.md`
- `@docs/issue-plan.md`
- `@docs/competitions.md`
