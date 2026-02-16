## API Deprecations

### Legacy `/api/*` Alias

Canonical API routes are versioned under `/api/v1/*`.

Compatibility aliases under `/api/*` remain available during migration and include:

- `Deprecation: true`
- `Sunset: Wed, 31 Dec 2026 23:59:59 GMT`
- `Link: </docs/api-deprecations#legacy-api>; rel="deprecation"`

Use `/api/v1/*` for all new integrations.

### `legacy-api` {#legacy-api}

Scope:

- `GET /api/me`, `GET /api/sessions/current`, `POST /api/sessions`, `POST /api/sessions/{id}/stop`
- `GET /api/auth/session-proxy`, `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`
- `GET /api/competitions`, `GET /api/competitions/{slug}`, `GET /api/competitions/{slug}/leaderboard`
- `POST /api/competitions/{slug}/submissions`, `GET /api/competitions/{slug}/submissions/me`
- `GET /api/datasets`, `GET /api/datasets/{slug}`
- `POST /api/admin/submissions/{submission_id}/score`

Migration guidance:

1. Replace `/api/` prefixes with `/api/v1/`.
2. Keep the same response envelope and problem-document parsing logic.
3. Keep using `meta.api_version` and problem `code` + `request_id` for diagnostics.
