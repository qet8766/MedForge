# MedForge API

FastAPI + SQLModel service for competition catalog, submissions, and leaderboard scoring.

Current alpha scope:

- Competition endpoints are implemented.
- Gate 2 auth foundations are implemented:
  - `POST /api/auth/signup`
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/me` (cookie auth; optional legacy header fallback via `ALLOW_LEGACY_HEADER_AUTH`)
  - `GET /api/auth/session-proxy` (owner/admin + running-session check)
- Gate 3 alpha lifecycle routes are implemented for PUBLIC sessions:
  - `POST /api/sessions` (PUBLIC create, PRIVATE returns `501`)
  - `POST /api/sessions/{id}/stop` (idempotent stop + snapshot terminalization)
- Gate 4 recovery paths are implemented in API:
  - startup reconciliation for `starting|running|stopping`
  - periodic poller for active session container-death detection

## Local Run

```bash
uv venv .venv
. .venv/bin/activate
uv pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Host runtime note: if running `SESSION_RUNTIME_MODE=docker` outside root, set `SESSION_RUNTIME_USE_SUDO=true` so ZFS/chown commands execute via `sudo -n`.

## Scoring Worker

```bash
python -m app.worker --once
python -m app.worker --interval 5 --batch-size 10
```

## Tests

```bash
pytest -q
```
