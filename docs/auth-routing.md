## 3. Authentication & Routing

Implementation status note (2026-02-16):

- Gate 2 auth foundations are implemented in API:
  - cookie-backed signup/login/logout and `/api/me`
  - `/api/auth/session-proxy` owner/admin authorization with running-session checks
- Gate 4 recovery orchestration is implemented (startup reconciliation + active-session poller).
- Gate 5 routing/isolation controls are in place; API auth matrix + spoof + east-west block + wildcard browser routing + websocket activity were validated on host (`@docs/host-validation-2026-02-16.md`).
- Competition APIs still allow temporary header identity fallback (`X-User-Id`) when `ALLOW_LEGACY_HEADER_AUTH=true`.

### Cookie Sessions

HTTP-only cookie session auth.

- Cookie attributes: `HttpOnly; Secure; SameSite=Lax; Domain=.medforge.<domain>; Path=/`
- CSRF/Origin guard: for all state-changing endpoints, reject if `Origin` is not an allowed MedForge origin.
- Cookie stores a random token (base64url). DB stores only a hash of the token (never raw).

### Wildcard Session Routing (Caddy + forward_auth)

Full Caddy config: `@infra/caddy/Caddyfile`

**forward_auth endpoint:** `GET /api/auth/session-proxy`

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

Caddy behaviour:

- Strips inbound `X-Upstream` from client request (prevents spoofing).
- Forwards cookie headers to the auth endpoint so wildcard subdomain requests are authorized with cookie sessions.
- Fails closed with 502 if `X-Upstream` is missing after auth.
- Proxies websockets natively (code-server terminal).
- Auth decisions are based on server-generated `X-Upstream` from `forward_auth`, never on client-provided upstream hints.

### East-West Isolation

Session containers must not reach other session containers' port 8080 over the Docker network. code-server runs with `--auth none`; Caddy/forward_auth is the only gate.

Firewall script: `@infra/firewall/setup.sh`

Rules applied to the `DOCKER-USER` chain:

- ALLOW TCP dport 8080 from Caddy's fixed IP (`172.30.0.2`) to the sessions bridge.
- DROP all other sources to TCP dport 8080 on the sessions bridge.
- `br_netfilter` is loaded and `net.bridge.bridge-nf-call-iptables=1` is set so bridge traffic is actually filtered.

**Acceptance test:** from inside session A, `curl http://mf-session-<slugB>:8080` must fail.
