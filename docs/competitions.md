# Competitions

### Scope

Competition API, scoring, and leaderboard runtime contract for alpha.

### In Scope

- competition domain terminology and seeded alpha competition set
- submission intake, scoring flow, and leaderboard ranking contract
- competition API surface and admin scoring endpoint behavior
- competition-specific response/error contract details

### Out of Scope

- dataset mirror filesystem and rehydration procedures (`docs/dataset-formats.md`)
- global auth/routing and wildcard policy (`docs/auth-routing.md`)
- schema/table-level definitions (`apps/api/app/models.py`, `apps/api/alembic/versions/`)
- operational run commands (`docs/runbook.md`)

### Canonical Sources

- `apps/api/app/routers/competitions/`
- `apps/api/app/services.py`
- `apps/api/app/scoring/`

## Terminology

- `competition_exposure` means platform policy (`external` or `internal`) and is not related to label visibility.
- `primary_score` is computed from hidden holdout labels.
- `scoring_mode` is `single_realtime_hidden` for alpha competitions.
- `leaderboard_rule` is `best_per_user` with deterministic ordering:
  - best `primary_score` (respecting `higher_is_better`)
  - then earliest score timestamp
  - then smallest submission ID
- `evaluation_policy` is `canonical_test_first`.
- Alpha has no due dates, no phase switches, and no `final_score` field.

## Alpha Competitions

- `titanic-survival` (metric: `accuracy`, cap: `20/day/user`)
- `rsna-pneumonia-detection` (metric: `map_iou`, cap: `10/day/user`)
- `cifar-100-classification` (metric: `accuracy`, cap: `20/day/user`)

Seed set includes EXTERNAL competitions and one INTERNAL competition (`oxford-pet-segmentation`).

## Submission and Scoring Flow

1. User uploads CSV to `POST /api/v2/external/competitions/{slug}/submissions` (or the matching `/internal/` route).
2. API validates schema and daily cap.
3. Submission is created as `score_status=queued`.
4. If `AUTO_SCORE_ON_SUBMIT=true` (default), API scores immediately; otherwise the worker scores asynchronously.
5. Scoring reads hidden holdout labels from `TEST_HOLDOUTS_DIR` and `manifest.json` metadata from `PUBLIC_EVAL_DATA_ROOT` (`evaluation_split_version`, policy fields, expected row count).
6. Scoring appends an official row in `submission_scores` with `primary_score`, `score_components_json`, `scorer_version`, `metric_version`, `evaluation_split_version`, and `manifest_sha256`.
7. Leaderboard ranks by best per-user official `primary_score`; deterministic tie-break uses earliest score timestamp then submission ID.

## API Surface

Canonical versioned routes:
- EXTERNAL surface:
  - `GET /api/v2/external/competitions` (`limit`, `cursor`)
  - `GET /api/v2/external/competitions/{slug}`
  - `GET /api/v2/external/competitions/{slug}/leaderboard` (`limit`, `cursor`)
  - `POST /api/v2/external/competitions/{slug}/submissions` (returns `201`)
  - `GET /api/v2/external/competitions/{slug}/submissions/me` (`limit`, `cursor`)
  - `GET /api/v2/external/datasets` (`limit`, `cursor`)
  - `GET /api/v2/external/datasets/{slug}`
- INTERNAL surface (requires `can_use_internal`):
- same route set under `/api/v2/internal/*`

## Router Module Structure

The competition API is implemented as a modular router package at `apps/api/app/routers/competitions/`:

- `catalog.py` — competition and dataset read endpoints
- `submissions.py` — submission upload and history
- `admin.py` — admin scoring trigger
- `leaderboard.py` — leaderboard SQL ranking query
- `submission_records.py` — submission row persistence helpers
- `queries.py` — shared DB query helpers
- `mappers.py` — ORM-to-response mapping
- `dependencies.py` — shared FastAPI dependencies
- `errors.py` — RFC 7807 error helpers

## Admin API

- `POST /api/v2/external/admin/submissions/{submission_id}/score`
- `POST /api/v2/internal/admin/submissions/{submission_id}/score`

## Response Contract

See `docs/architecture.md` > **API Response Contract** for the canonical envelope and error format.

## Security and Data Policy

- Hidden holdout labels are stored server-side only and are never mounted in user sessions.
- Competition dataset mirrors are intended for controlled internal deployment.
