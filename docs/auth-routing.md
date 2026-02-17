## 3. Authentication & Routing

Implementation status note (2026-02-16):

- Phase 2 auth foundations are implemented in API:
  - cookie-backed signup/login/logout and `/api/v1/me`
  - `/api/v1/auth/session-proxy` owner/admin authorization with running-session checks
- Phase 3 recovery orchestration is implemented (startup reconciliation + active-session poller).
- Phase 4 routing/isolation controls are implemented; canonical validation uses `@docs/phase-checking-strategy.md`.
- Legacy header identity fallback (`X-User-Id`) is removed from API auth paths.
- Competition submission uploads are bounded by `SUBMISSION_UPLOAD_MAX_BYTES` (default `10485760`).

### Cookie Sessions

HTTP-only cookie session auth.

- Cookie attributes: `HttpOnly; Secure; SameSite=Lax; Domain=.medforge.<domain>; Path=/`
- CSRF/Origin guard: for all state-changing endpoints, reject if `Origin` is not an allowed MedForge origin.
- Cookie stores a random token (base64url). DB stores only a hash of the token (never raw).
- Competition write endpoints covered by origin guard: `POST /api/v1/competitions/{slug}/submissions` and `POST /api/v1/admin/submissions/{submission_id}/score`.
- Admin scoring endpoint authorization is cookie principal role-based (`role=admin`); no `X-Admin-Token` bypass.

### Wildcard Session Routing (Caddy + forward_auth)

Full Caddy config: `@deploy/caddy/Caddyfile`

**forward_auth endpoint:** `GET /api/v1/auth/session-proxy`

Inputs:

- `Host: s-<slug>.medforge.<domain>`
- Cookie session

FastAPI returns:

| Code | Condition                                                  | Header                               |
| ---- | ---------------------------------------------------------- | ------------------------------------ |
| 200  | Authenticated, owns session (or admin), session is running | `X-Upstream: mf-session-<slug>:8080` |
| 401  | Not authenticated                                          |                                      |
| 403  | Authenticated but not owner/admin                          |                                      |
| 404  | Slug not found or session not running                      |                                      |

Success and error payloads follow the global API contract:

- success: `{ "data": ..., "meta": { request_id, ... } }`
- error: `application/problem+json` with `type`, `title`, `status`, `detail`, `instance`, `code`, `request_id`, and optional `errors`.

Caddy behaviour:

- Strips inbound `X-Upstream` from client request (prevents spoofing).
- Forwards cookie headers to the auth endpoint so wildcard subdomain requests are authorized with cookie sessions.
- Fails closed with 502 if `X-Upstream` is missing after auth.
- Proxies websockets natively (code-server terminal).
- Auth decisions are based on server-generated `X-Upstream` from `forward_auth`, never on client-provided upstream hints.

### East-West Isolation

Session containers must not reach other session containers' port 8080 over the Docker network. code-server runs with `--auth none`; Caddy/forward_auth is the only enforcement boundary.

Firewall script: `@ops/network/firewall-setup.sh`

Rules applied to the `DOCKER-USER` chain:

- ALLOW TCP dport 8080 from Caddy's fixed IP (`172.30.0.2`) to the sessions bridge.
- DROP all other sources to TCP dport 8080 on the sessions bridge.
- `br_netfilter` is loaded and `net.bridge.bridge-nf-call-iptables=1` is set so bridge traffic is actually filtered.

**Acceptance test:** from inside session A, `curl http://mf-session-<slugB>:8080` must fail.
