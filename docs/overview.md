## 1. Overview

MedForge provisions GPU-backed development sessions (code-server in the browser) on a single multi-GPU Ubuntu host. Sessions run in a single default immutable Pack (Docker image digest pinned) to avoid dependency drift. Each session gets an isolated ZFS workspace dataset with snapshots-on-stop for rollback.

Current implementation note (2026-02-16):

- Competition APIs/UI and scoring are implemented.
- Gate 2 auth foundations are implemented (cookie auth endpoints, `/api/me`, and session-proxy auth checks).
- Gate 3 alpha lifecycle is implemented for PUBLIC create/stop, including allocation and snapshot terminalization.
- Gate 4 recovery behavior is implemented (startup reconciliation + active-session poller).
- Gate 5/6 host evidence is partially complete (`@docs/host-validation-2026-02-16.md`): auth matrix, spoof resistance, east-west block, GPU visibility, workspace write, and snapshot checks passed.
- Remaining in-progress checks are Caddy websocket validation and UI-driven full browser smoke.

### Goals

- Launch PUBLIC sessions: browser VS Code (code-server) + terminal + GPU access.
- Launch permanent PUBLIC mock competitions with leaderboard scoring (`titanic-survival`, `rsna-pneumonia-detection`).
- Enforce 1 GPU per session and max 7 concurrent sessions (one per physical GPU).
- Enforce per-user concurrent session limits.
- Wildcard subdomains per session: `s-<slug>.medforge.<domain>`.
- Persist per-session workspaces on ZFS; take a snapshot on session stop.
- Structured JSON event logs to stdout (login + session lifecycle).

### Constraints

- Single host (Ubuntu 24.04 LTS).
- Stack: **Next.js + TypeScript**, **FastAPI + SQLModel**, **MariaDB**.
- code-server is the in-browser IDE.
- Competition scoring uses a hidden holdout split and `leaderboard_score` only (no alpha finals phase).
- PRIVATE tier defined but returns 501; no egress restrictions, audited access, or UI transfer controls enforced.

### Non-Goals

- Forums, marketplace.
- Dataset registry / managed read-only mounts.
- Exfiltration prevention against screenshots/copying.
- Enterprise auth (SSO/SCIM).
- Multi-node scheduling.
- Lease TTL/heartbeat renewal (explicit stop + container state polling + boot-time reconciliation only).
- Scheduled snapshot policies / retention automation.
- Snapshot restore tooling (manual admin ZFS ops only).
- Observability stack beyond structured API logs + host tools.
