## 2. Architecture

Implementation status note (2026-02-16):

- Competition-plane components are implemented (`medforge-web`, `medforge-api`, `medforge-db`, `medforge-caddy`, and `medforge-api-worker`).
- Session lifecycle and recovery orchestration are implemented in API for PUBLIC alpha sessions.
- Host-level Gate 5/6 validation is completed (auth matrix, upstream-header spoof resistance, east-west session isolation, GPU/workspace/snapshot checks, and browser wildcard websocket lane) with evidence in `@docs/host-validation-2026-02-16.md`.

### Control Plane

| Component        | Role                                     |
| ---------------- | ---------------------------------------- |
| **medforge-web** | Next.js frontend                         |
| **medforge-api** | FastAPI session + competition APIs       |
| **MariaDB**      | Persistent state                         |
| **Caddy**        | Reverse proxy + wildcard TLS + auth gate |

### Data Plane

- Per-session Docker containers running code-server.
- Persistent per-session workspaces mounted from ZFS.
- Competition submission scoring worker processes queued CSV submissions against hidden holdout labels.

Full control-plane composition: `@infra/compose/docker-compose.yml`
Compose env template: `@infra/compose/.env.example`
`medforge-web` server-side data fetches can use `API_URL` (for example `http://medforge-api:8000` inside Compose).

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
| Data ingestion     | User fetch + internal mirrored competition data | Controlled            |
| Audit              | Structured JSON logs to stdout       | Strict auditing       |
| Status             | **Available**                        | **501 Not Available** |

### Domains & TLS

| Subdomain                    | Target            |
| ---------------------------- | ----------------- |
| `medforge.<domain>`          | Next.js           |
| `api.medforge.<domain>`      | FastAPI           |
| `s-<slug>.medforge.<domain>` | Session container |

Wildcard cert `*.medforge.<domain>` via Caddy DNS challenge. Single wildcard cert, no per-session issuance. Routing config: `@infra/caddy/Caddyfile`. Caddy image build: `@infra/caddy/Dockerfile`

### Repo Layout

```
apps/
  web/                  # Next.js App Router (competitions, datasets, submit flow)
  api/                  # FastAPI + SQLModel
    app/                # API routes, models, scoring, worker
    tests/              # pytest coverage for competition API/scoring
    alembic/            # Alembic environment + versioned migrations
    data/competitions/  # holdout label sets + manifest versions
infra/
  caddy/                # Caddyfile, Caddy Dockerfile (DNS plugin)
  compose/              # docker-compose, .env.example
  packs/
    default/            # Session Dockerfile + pinned basic/extras dependency manifests
  zfs/                  # ZFS pool/dataset setup
  firewall/             # East-west isolation iptables rules
```

### Storage

ZFS setup script: `@infra/zfs/setup.sh`

#### Workspaces

Dataset layout:

```
tank/medforge/workspaces/<user_id>
tank/medforge/workspaces/<user_id>/<session_id>
tank/medforge/system/db
```

Each session mounts only its own dataset (`.../<session_id>`), even when a user has multiple concurrent sessions.

All packs run as a fixed non-root UID/GID (1000:1000). On session workspace dataset creation, set mount ownership to that UID/GID. Optional hard quota applied at dataset creation time. No warning system.

#### Snapshots

Taken on session stop only: `<session_dataset>@stop-<unixms>`.

No scheduled snapshots, retention automation, or restore API/UI. Restore is manual admin ZFS ops.
