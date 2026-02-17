# MedForge API

FastAPI + SQLModel service for competition catalog, submissions, and leaderboard scoring.

Current alpha scope:

- Competition endpoints are implemented.
- Phase 2 auth foundations are implemented:
- `POST /api/v2/auth/signup`
- `POST /api/v2/auth/login`
- `POST /api/v2/auth/logout`
- `GET /api/v2/me` (cookie auth + `can_use_internal`)
- `GET /api/v2/auth/session-proxy` (owner/admin + running-session check)
- Session lifecycle routes are exposure-split in v2:
  - `POST /api/v2/external/sessions`
  - `POST /api/v2/internal/sessions` (requires `can_use_internal`)
  - `POST /api/v2/external/sessions/{id}/stop`
  - `POST /api/v2/internal/sessions/{id}/stop`
- Phase 3 recovery paths are implemented in API:
  - startup reconciliation for `starting|running|stopping`
  - periodic poller for active session container-death detection

## Local Run

```bash
uv venv .venv
. .venv/bin/activate
uv pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

## Migrations (Alembic)

```bash
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "describe_change"
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
