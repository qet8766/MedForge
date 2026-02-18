# MedForge Operational Runbook

Day-2 operational procedures for the MedForge platform.

### Scope

### In Scope

- operator commands for restart, reconciliation, cleanup, logs, and health checks
- troubleshooting playbooks for common runtime failures
- canonical validation command entry points for operations execution

### Out of Scope

- normative runtime/API contracts (`docs/architecture.md`, `docs/sessions.md`, `docs/auth-routing.md`, `docs/competitions.md`)
- schema/entity definitions (`apps/api/app/models.py`, `apps/api/alembic/versions/`)
- phase acceptance criteria ownership (`docs/phase-checking-strategy.md`)

### Canonical Sources

- `ops/host/`
- `ops/network/firewall-setup.sh`
- `ops/storage/`
- `deploy/compose/docker-compose.yml`
- `deploy/caddy/Caddyfile`

## Service Architecture

```
User → Caddy (wildcard TLS) → FastAPI (medforge-api) → Docker (mf-session-*)
                                    ↓
                          medforge-api-worker (async scoring)
                                    ↓
                               MariaDB (medforge-db) + ZFS snapshots
```

Key services in `deploy/compose/docker-compose.yml`:
- `medforge-api` — FastAPI control plane
- `medforge-api-worker` — Background submission scoring worker
- `medforge-db` — MariaDB system of record
- `medforge-caddy` — TLS termination + wildcard session routing
- `medforge-web` — Next.js frontend

Host mount prerequisite:
- `medforge-api` must mount `/tank:/tank` so runtime workspace ownership/quota commands affect host ZFS mountpoints.
- On `medforge-external-sessions`, reserve fixed IPs to avoid startup races: `medforge-caddy=172.30.0.2`, `medforge-api=172.30.0.3`.

Routing operation note:
- Validate session reachability against wildcard root (`https://s-<slug>.medforge.<domain>/`).
- For normative wildcard auth behavior, use `docs/auth-routing.md`.

## Common Operations

### Restart Services

```bash
# Restart all services
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml restart

# Restart just the API (triggers boot reconciliation)
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml restart medforge-api

# Full rebuild and restart
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build
```

### Trigger Reconciliation

The API runs `reconcile_on_startup` automatically on boot. To trigger manually:

```bash
bash ops/host/ops-reconcile.sh
```

This restarts the API service, which:
1. Reconciles STARTING sessions (marks ERROR if container is missing)
2. Completes STOPPING sessions (stop + snapshot + finalize)
3. Normalizes RUNNING sessions (updates container_id if needed)

### Inspect ZFS Snapshots

```bash
# List all session snapshots
bash ops/host/ops-snapshots.sh

# Filter by session slug
bash ops/host/ops-snapshots.sh abc12345

# Filter by user UUID
bash ops/host/ops-snapshots.sh --user 00000000-0000-0000
```

### Clean Up Orphaned Containers

```bash
# Dry run — list orphans without removing
bash ops/host/ops-cleanup.sh

# Force removal
bash ops/host/ops-cleanup.sh --force
```

### View Logs

```bash
# Stream API and Caddy logs
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml logs -f medforge-api medforge-caddy

# Session container logs
docker logs mf-session-<slug>

# API structured logs contain: session_id, user_id, slug, event name
```

### Canonical Validation

Canonical phase validation is remote-external only.

```bash
# Policy guard (fails if repo code reintroduces local/split validation modes)
bash ops/host/validate-policy-remote-external.sh

# Full remote-external phase progression
bash ops/host/validate-phases-all.sh

# Phase 4 only (remote-external routing/isolation/browser/websocket)
bash ops/host/validate-phase4-routing-e2e.sh
```

## Health Checks

```bash
# API health
curl https://api.medforge.<domain>/healthz

# Returns {"data":{"status":"ok"}} when healthy
# Returns 503 {"data":{"status":"degraded"}} when recovery thread is dead
```

## Troubleshooting

### Session Stuck in STARTING

**Symptoms:** Session shows `starting` status indefinitely.

**Diagnosis:**
```bash
# Check if container exists
docker ps -a --filter "name=mf-session-<slug>"

# Check API logs for the session
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml logs medforge-api 2>&1 | grep "<slug>"
```

**Resolution:**
1. Run reconciliation: `bash ops/host/ops-reconcile.sh`
2. The reconcile pass will mark STARTING sessions with missing containers as ERROR

### Session Stuck in STOPPING

**Symptoms:** Session shows `stopping` but never completes.

**Diagnosis:**
```bash
# Check if container is still running
docker inspect mf-session-<slug> --format '{{.State.Status}}'

# Check for stop/snapshot errors in logs
docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml logs medforge-api 2>&1 | grep "session.recovery.failure"
```

**Resolution:**
1. Run reconciliation: `bash ops/host/ops-reconcile.sh`
2. If stop keeps failing, manually remove: `docker rm -f mf-session-<slug>`
3. Run reconciliation again to finalize the database state

### GPU Exhaustion (No GPUs Available)

**Symptoms:** `409 No GPUs available` on session create.

**Diagnosis:**
```bash
# List all session containers
docker ps --filter "name=mf-session-"

# Check for orphaned containers holding GPU locks
bash ops/host/ops-cleanup.sh
```

**Resolution:**
1. Clean up orphaned containers: `bash ops/host/ops-cleanup.sh --force`
2. Run reconciliation to free GPU locks: `bash ops/host/ops-reconcile.sh`

### Recovery Thread Dead (503 on /healthz)

**Symptoms:** `/healthz` returns 503 with `{"status":"degraded"}`.

**Resolution:**
1. Restart the API service: `bash ops/host/ops-reconcile.sh`
2. Check logs for the cause of the thread crash

## Escalation Path

1. **Self-service:** Run reconciliation + cleanup scripts
2. **Service restart:** `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml restart medforge-api`
3. **Full rebuild:** `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build`
4. **Host reboot:** Last resort; all sessions will be reconciled on API boot
