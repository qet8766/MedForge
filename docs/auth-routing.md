# Authentication and Routing

### Scope

Authentication and routing contract for external MedForge hosts.

### In Scope

- cookie session authentication for API principals
- origin allowlist checks on state-changing API routes
- session access model (SSH with public-key auth, port range 10000–10999)

### Out of Scope

- session lifecycle/recovery internals (`docs/sessions.md`)
- competition upload/scoring policy and limits (`docs/competitions.md`)
- host firewall implementation and operations runbook (`docs/runbook.md`)

### Canonical Sources

- `deploy/caddy/Caddyfile`
- `apps/api/app/deps.py`
- `apps/api/app/routers/auth.py`
- `apps/api/app/routers/control_plane.py`

## Cookie Session Contract

- Signup/login set a cookie token (`COOKIE_NAME`, default `medforge_session`) with:
  - `HttpOnly`
  - `Secure` from `COOKIE_SECURE` (default `true`)
  - `SameSite` from `COOKIE_SAMESITE` (default `lax`)
  - `Domain` from `COOKIE_DOMAIN` (default `.medforge.<domain>` when `DOMAIN` is set)
  - `Path=/`
- Cookie stores a random session token; database stores only its hash.
- `GET /api/v2/me` authenticates using the cookie principal.
- `POST /api/v2/auth/logout` revokes the active token hash and clears the cookie.
- Session validity enforces both idle and max TTL (`AUTH_IDLE_TTL_SECONDS`, `AUTH_MAX_TTL_SECONDS`).

## Origin Allowlist Contract

- Guard behavior: if an `Origin` header is present and not allowed, API returns `403`.
- Allowed origins match MedForge hosts under configured `DOMAIN`:
  - `medforge.<domain>`
  - `api.medforge.<domain>`
  - `*.medforge.<domain>`
- No `Origin` header is accepted by this guard.
- Guarded state-changing endpoints:
  - `POST /api/v2/auth/signup`
  - `POST /api/v2/auth/login`
  - `POST /api/v2/auth/logout`
  - `POST /api/v2/external/sessions`
  - `POST /api/v2/internal/sessions`
  - `POST /api/v2/external/sessions/{id}/stop`
  - `POST /api/v2/internal/sessions/{id}/stop`
  - `POST /api/v2/external/competitions/{slug}/submissions`
  - `POST /api/v2/internal/competitions/{slug}/submissions`
  - `POST /api/v2/external/admin/submissions/{submission_id}/score`
  - `POST /api/v2/internal/admin/submissions/{submission_id}/score`

## Session Access Model

Session containers run sshd on port 22. The API allocates a host SSH port (range 10000–10999) per session and maps it to the container's port 22. Users connect via `ssh -p <port> coder@<domain>`.

There is no wildcard HTTP routing to session containers — Caddy does not proxy to sessions. Access control is enforced by SSH public-key authentication: the user's configured SSH public key is injected into the container at startup.

## Response Contract

See `docs/architecture.md` > **API Response Contract** for the canonical envelope and error format.
