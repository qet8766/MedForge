-- Competition schema hardening:
-- - enforce non-negative/positive numeric invariants
-- - add a covering index for per-user daily submission cap checks

ALTER TABLE datasets
  ADD CONSTRAINT ck_datasets_bytes_nonnegative CHECK (bytes >= 0);

ALTER TABLE competitions
  ADD CONSTRAINT ck_competitions_submission_cap_positive CHECK (submission_cap_per_day > 0);

ALTER TABLE submissions
  ADD CONSTRAINT ck_submissions_row_count_nonnegative CHECK (row_count >= 0);

CREATE INDEX ix_submissions_competition_user_created
  ON submissions (competition_id, user_id, created_at);
