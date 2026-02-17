## 2. Architecture

Implementation status note (2026-02-16):

- Competition-plane components are implemented (`medforge-web`, `medforge-api`, `medforge-db`, `medforge-caddy`, and `medforge-api-worker`).
- Session lifecycle and recovery orchestration are implemented in API for PUBLIC alpha sessions.
- Historical pre-phase host validation artifacts were retired from the repo; canonical validation now uses `@docs/phase-checking-strategy.md`.

### Control Plane

| Component        | Role                                     |
| ---------------- | ---------------------------------------- |
| **medforge-web** | Next.js frontend                         |
| **medforge-api** | FastAPI session + competition APIs       |
| **MariaDB**      | Persistent state                         |
| **Caddy**        | Reverse proxy + wildcard TLS + auth boundary |

### Data Plane

- Per-session Docker containers running code-server.
- Persistent per-session workspaces mounted from ZFS.
- Competition submission scoring worker processes queued CSV submissions against hidden holdout labels.

Full control-plane composition: `@deploy/compose/docker-compose.yml`
Compose env template: `@deploy/compose/.env.example`
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

Wildcard cert `*.medforge.<domain>` via Caddy DNS challenge. Single wildcard cert, no per-session issuance. Routing config: `@deploy/caddy/Caddyfile`. Caddy image build: `@deploy/caddy/Dockerfile`

### Repo Layout

```
apps/
  web/                  # Next.js App Router (competitions, datasets, submit flow)
  api/                  # FastAPI + SQLModel
    app/                # API routes, models, scoring, worker
    app/session_runtime/ # Session runtime ports/adapters, DTOs, and factory
    tests/              # pytest coverage for competition API/scoring
    alembic/            # Alembic environment + versioned migrations
    data/competitions/  # holdout label sets + manifest versions
deploy/
  caddy/                # Caddyfile, Caddy Dockerfile (DNS plugin)
  compose/              # docker-compose, .env.example
  packs/
    default/            # Session Dockerfile + pinned basic/extras dependency manifests
ops/
  host/                 # bootstrap, validation, and operational scripts
  storage/              # ZFS pool/dataset setup
  network/              # East-west isolation iptables rules
datasets/               # full mirrored competition datasets (large payloads)
tools/
  data-prep/            # dataset preparation/re-hydration helpers
```

### Storage

ZFS setup script: `@ops/storage/zfs-setup.sh`
Bootstrap provisioning: `@ops/host/bootstrap-easy.sh`

#### Pool Configuration

Production pool uses RAIDZ1 across 4x NVMe drives (e.g. Samsung 9100 PRO 8TB). Pool creation options:

| Option | Value | Purpose |
| --- | --- | --- |
| `ashift` | 12 | 4K sector alignment |
| `autotrim` | on | SSD TRIM passthrough |
| `compression` | lz4 | Inline compression |
| `atime` | off | Disable access-time updates |
| `xattr` | sa | Store extended attributes in inodes |
| `dnodesize` | auto | Variable dnode sizing |
| `normalization` | formD | Unicode normalization |
| `relatime` | on | Reduced atime overhead |

Host-level datasets `tank/data` and `tank/docker` are created manually (host-specific). The bootstrap script configures Docker `data-root` to `/tank/docker`.

#### Host Tuning

- **ARC cap**: 32 GiB (`/etc/modprobe.d/zfs.conf` + live sysfs write).
- **Weekly scrub**: cron job at 02:00 Sunday (`/etc/cron.d/zfs-scrub`).

Both are applied by `ensure_zfs_tuning()` in the bootstrap script.

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
