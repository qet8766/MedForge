## Authentication & Routing

> V2 Update (2026-02-17): API/auth contract is now `/api/v2/*` with exposure split.
> - Shared auth: `/api/v2/auth/*`, `/api/v2/me`
> - Guarded state-changing endpoints are under `/api/v2/external/*` and `/api/v2/internal/*`
> - Session wildcard hosts are exposure-qualified (`*.external.medforge.<domain>`, `*.internal.medforge.<domain>`).
> Any remaining non-split route examples below are legacy and superseded by the v2 exposure contract.

Implementation status note (2026-02-17):

- Canonical remote-public validation is `PASS` through Phase 5 (`@docs/phase-checking-strategy.md`, `@docs/validation-logs.md`).
- Auth contract evidence: `@docs/evidence/2026-02-17/phase2-auth-api-20260217T064639Z.md`.
- Routing boundary evidence: `@docs/evidence/2026-02-17/phase4-routing-e2e-20260217T064739Z.md`.

### Scope

Authentication and wildcard routing contract for public MedForge hosts.

### In Scope

- cookie session authentication for API principals
- origin allowlist checks on state-changing API routes
- wildcard routing trust chain (`Caddy forward_auth -> API session-proxy -> upstream`)
- upstream spoof-resistance and internal-path blocking on wildcard hosts

### Out of Scope

- session lifecycle/recovery internals (`@docs/sessions.md`)
- competition upload/scoring policy and limits (`@docs/competitions.md`)
- host firewall implementation and operations runbook (`@docs/runbook.md`)

### Canonical Sources

- `@docs/phase-checking-strategy.md`
- `@docs/validation-logs.md`
- `@docs/evidence/2026-02-17/phase2-auth-api-20260217T064639Z.md`
- `@docs/evidence/2026-02-17/phase4-routing-e2e-20260217T064739Z.md`
- `@deploy/caddy/Caddyfile`
- `@apps/api/app/deps.py`
- `@apps/api/app/routers/auth.py`
- `@apps/api/app/routers/control_plane.py`

### Cookie Session Contract

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

### Origin Allowlist Contract

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

### Wildcard Routing Contract (Caddy + forward_auth)

Full config: `@deploy/caddy/Caddyfile`

Internal authorization endpoint:

- `GET /api/v2/auth/session-proxy` (API host path used by Caddy `forward_auth`)

Wildcard host protections:

- External callers to `https://s-<slug>.external.medforge.<domain>/api/v2/auth/session-proxy` and
  `https://s-<slug>.internal.medforge.<domain>/api/v2/auth/session-proxy` are blocked with `403` by Caddy.
- Client-supplied `X-Upstream` is stripped before auth.

`session-proxy` authorization matrix:

| Code | Condition                                                  | Header                               |
| ---- | ---------------------------------------------------------- | ------------------------------------ |
| 200  | Authenticated, owner/admin, and session is `running`      | `X-Upstream: mf-session-<slug>:8080` |
| 401  | Not authenticated                                          |                                      |
| 403  | Authenticated but not owner/admin                          |                                      |
| 404  | Invalid session host, unknown slug, or session not running |                                      |

Caddy trust chain:

- forwards `Host` and cookie context to `session-proxy`
- copies API-generated `X-Upstream` to internal header `X-Medforge-Upstream`
- fails closed with `502` if upstream header is missing
- reverse proxies to `X-Medforge-Upstream`; websocket transport is supported
- upstream choice is authoritative only from API-generated header, never client input

### Response Contract

- Success responses: envelope `{ "data": ..., "meta": { request_id, ... } }`
- Error responses: `application/problem+json` with `type`, `title`, `status`, `detail`, `instance`, `code`, `request_id`, and optional `errors`
