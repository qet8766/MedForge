## 10. Competitions (Alpha)

MedForge alpha includes permanent mock competitions with Kaggle-style submissions and leaderboards.

### Terminology

- `competition_tier` means platform policy (`PUBLIC` or `PRIVATE`) and is not related to label visibility.
- `leaderboard_score` is computed from hidden holdout labels.
- Alpha has no due dates, no phase switches, and no `final_score` field.

### Alpha Competitions

- `titanic-survival` (metric: `accuracy`, cap: `20/day/user`)
- `rsna-pneumonia-detection` (metric: `roc_auc`, cap: `10/day/user`)

Both are `competition_tier=PUBLIC`.

### Submission and Scoring Flow

1. User uploads CSV to `POST /api/competitions/{slug}/submissions`.
2. API validates schema and daily cap.
3. Submission is created as `score_status=queued`.
4. If `AUTO_SCORE_ON_SUBMIT=true` (default), API scores immediately; otherwise the worker scores asynchronously.
5. Scoring writes `leaderboard_score`, `scorer_version`, and `evaluation_split_version`.
6. Leaderboard ranks by best per-user `leaderboard_score`; tie-breaker is earliest submission timestamp.

### Alpha API Surface

- `GET /api/competitions`
- `GET /api/competitions/{slug}`
- `GET /api/competitions/{slug}/leaderboard`
- `POST /api/competitions/{slug}/submissions`
- `GET /api/competitions/{slug}/submissions/me`
- `GET /api/datasets`
- `GET /api/datasets/{slug}`

### Security and Data Policy

- Hidden holdout labels are stored server-side only and are never mounted in user sessions.
- Competition dataset mirrors are intended for internal/private deployment.
- Public internet redistribution of mirrored Kaggle competition assets is out of scope.
