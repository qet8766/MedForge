---
description: Rebuild and restart MedForge server components
allowed-tools: [Bash, Read, Glob, Grep]
---

You are rebuilding MedForge server components. Follow the container rebuild policy from `docs/runbook.md`.

## Procedure

1. Check `git diff --name-only HEAD` (or recent unstaged changes) to determine which source paths changed
2. Map changed paths to affected services using this policy:

   | Source path | Affected service(s) | Command |
   | --- | --- | --- |
   | `apps/api/**` | `medforge-api`, `medforge-api-worker` | `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build medforge-api medforge-api-worker` |
   | `apps/web/**` | `medforge-web` | `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build medforge-web` |
   | `deploy/caddy/Caddyfile` | `medforge-caddy` | `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml restart medforge-caddy` |
   | `deploy/caddy/Dockerfile` | `medforge-caddy` | `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build medforge-caddy` |
   | `deploy/compose/.env` | all services | `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build` |
   | `deploy/compose/docker-compose.yml` | affected service(s) | `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d <service>` |
   | `deploy/packs/**` | session containers (new sessions) | `docker build -t medforge-pack-default:local deploy/packs/default && docker images medforge-pack-default:local --digests --no-trunc` — then update `PACK_IMAGE` in `deploy/compose/.env` with new digest |

3. If the user passed an argument (e.g., `/rebuild all` or `/rebuild api`), use that to override detection:
   - `all` → full rebuild: `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml up -d --build`
   - `api` → `medforge-api medforge-api-worker`
   - `web` → `medforge-web`
   - `caddy` → `medforge-caddy`
   - `pack` → rebuild pack image: `docker build -t medforge-pack-default:local deploy/packs/default`, then update `PACK_IMAGE` in `deploy/compose/.env` with new digest, then restart `medforge-api medforge-api-worker`

4. Run the appropriate docker compose command(s)
5. After rebuild, verify:
   - `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml ps` — all target services should be "Up"
   - `curl -fsS https://api.medforge.xyz/healthz` — should return 200
6. Report which services were rebuilt and their status
7. **Pack image note**: Pack rebuilds only affect newly created sessions. Existing running sessions continue with the previous image. After updating `PACK_IMAGE` in `.env`, restart `medforge-api` and `medforge-api-worker` so they pick up the new image reference.
