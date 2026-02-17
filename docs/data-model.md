## Data Model

### Enums

| Enum          | Values                                                     |
| ------------- | ---------------------------------------------------------- |
| Tier          | `PUBLIC`, `PRIVATE`                                        |
| Role          | `user`, `admin`                                            |
| SessionStatus | `starting`, `running`, `stopping`, `stopped`, `error`      |
| PackTier      | `PUBLIC`, `PRIVATE`, `BOTH`                                |

### Tables

#### users

| Column                  | Type     | Notes     |
| ----------------------- | -------- | --------- |
| id                      | UUID     | PK        |
| email                   | string   | unique    |
| password_hash           | string   |           |
| role                    | Role     |           |
| max_concurrent_sessions | int      | default 1, `CHECK > 0` |
| created_at              | datetime |           |

#### auth_sessions

| Column       | Type     | Notes       |
| ------------ | -------- | ----------- |
| id           | UUID     | PK          |
| user_id      | UUID     | FK -> users |
| token_hash   | string   |             |
| created_at   | datetime |             |
| expires_at   | datetime |             |
| revoked_at   | datetime | nullable    |
| last_seen_at | datetime | nullable    |
| ip           | string   | optional    |
| user_agent   | string   | optional    |

#### packs (single seeded row)

| Column        | Type     | Notes    |
| ------------- | -------- | -------- |
| id            | UUID     | PK       |
| name          | string   |          |
| tier          | PackTier |          |
| image_ref     | string   |          |
| image_digest  | string   |          |
| created_at    | datetime |          |
| deprecated_at | datetime | nullable |

#### gpu_devices (seed rows 0-6, all enabled)

| Column  | Type | Notes     |
| ------- | ---- | --------- |
| id      | int  | PK (0..6) |
| enabled | bool |           |

#### sessions

| Column        | Type          | Notes                           |
| ------------- | ------------- | ------------------------------- |
| id            | UUID          | PK                              |
| user_id       | UUID          | FK -> users                     |
| tier          | Tier          |                                 |
| pack_id       | UUID          | FK -> packs                     |
| status        | SessionStatus |                                 |
| container_id  | string        | nullable                        |
| gpu_id        | int           | FK -> gpu_devices, NOT NULL     |
| slug          | string        | unique, 8-char lowercase base32 |
| workspace_zfs | string        | session dataset path (`tank/medforge/workspaces/<user_id>/<session_id>`), unique |
| created_at    | datetime      |                                 |
| started_at    | datetime      | nullable                        |
| stopped_at    | datetime      | nullable                        |
| error_message | string        | nullable                        |
| gpu_active    | int           | generated; non-null only for active states, NULL when terminal |

**GPU exclusivity via generated column + unique index:**

```sql
gpu_active = CASE WHEN status IN ('starting', 'running', 'stopping') THEN 1 ELSE NULL END

UNIQUE(gpu_id, gpu_active)
```

Enforces at most one active session per GPU at the DB level.

**Slug generation:** 8-char lowercase base32, no padding. Generate and retry up to 3 times for uniqueness.

## 6.1 Competition Platform (Alpha)

Important terminology:

- `competition_tier` (`PUBLIC` | `PRIVATE`) is platform policy (internet/data controls), not label visibility.
- `primary_score` is computed on hidden holdout labels and stored in append-only score runs.
- `scoring_mode` is realtime hidden scoring contract (`single_realtime_hidden` in alpha).
- `leaderboard_rule` defines ranking (`best_per_user` in alpha).
- `evaluation_policy` captures split provenance policy (`canonical_test_first`).
- Alpha competitions are permanent (`is_permanent=true`) and have no due dates/final phase.

### Enums

| Enum              | Values                                |
| ----------------- | ------------------------------------- |
| CompetitionTier   | `PUBLIC`, `PRIVATE`                   |
| CompetitionStatus | `active`, `inactive`                  |
| ScoreStatus       | `queued`, `scoring`, `scored`, `failed` |

### datasets

| Column       | Type     | Notes |
| ------------ | -------- | ----- |
| id           | UUID     | PK |
| slug         | string   | unique |
| title        | string   | |
| source       | string   | e.g. `kaggle` |
| license      | string   | |
| storage_path | string   | mirrored path |
| bytes        | int      | `CHECK >= 0` |
| checksum     | string   | |
| created_at   | datetime | |

### competitions

| Column                 | Type              | Notes |
| ---------------------- | ----------------- | ----- |
| id                     | UUID              | PK |
| slug                   | string            | unique |
| title                  | string            | |
| description            | string            | |
| competition_tier       | CompetitionTier   | policy tier |
| status                 | CompetitionStatus | |
| is_permanent           | bool              | true for alpha |
| metric                 | string            | e.g. `accuracy`, `map_iou` |
| metric_version         | string            | e.g. `accuracy-v1`, `map_iou-v1` |
| higher_is_better       | bool              | default true |
| scoring_mode           | string            | e.g. `single_realtime_hidden` |
| leaderboard_rule       | string            | e.g. `best_per_user` |
| evaluation_policy      | string            | e.g. `canonical_test_first` |
| competition_spec_version | string          | scoring contract version |
| submission_cap_per_day | int               | per-user cap, `CHECK > 0` |
| dataset_id             | UUID              | FK -> datasets |
| created_at             | datetime          | |
| updated_at             | datetime          | |

### submissions

| Column                   | Type       | Notes |
| ------------------------ | ---------- | ----- |
| id                       | UUID       | PK |
| competition_id           | UUID       | FK -> competitions |
| user_id                  | UUID       | participant |
| filename                 | string     | original upload name |
| artifact_path            | string     | stored CSV path |
| artifact_sha256          | string     | integrity hash |
| row_count                | int        | `CHECK >= 0` |
| score_status             | ScoreStatus | |
| score_error              | string     | nullable |
| created_at               | datetime   | |
| scored_at                | datetime   | nullable |

### submission_scores

| Column                   | Type      | Notes |
| ------------------------ | --------- | ----- |
| id                       | UUID      | PK |
| submission_id            | UUID      | FK -> submissions |
| competition_id           | UUID      | FK -> competitions |
| user_id                  | UUID      | copied for leaderboard queries |
| is_official              | bool      | one current official run per submission |
| primary_score            | float     | canonical rank score |
| score_components_json    | string    | JSON object of metric components |
| scorer_version           | string    | evaluator build/version |
| metric_version           | string    | metric algorithm version |
| evaluation_split_version | string    | holdout split version |
| manifest_sha256          | string    | manifest integrity hash |
| created_at               | datetime  | scoring run timestamp |

`UNIQUE(submission_id, scorer_version, metric_version, evaluation_split_version, manifest_sha256)` — idempotent scoring runs.
