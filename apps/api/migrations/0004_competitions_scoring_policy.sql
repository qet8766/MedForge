-- Competition scoring policy metadata for API/UI contract.
-- Keeps score visibility terms separate from competition_tier PUBLIC/PRIVATE.

ALTER TABLE competitions
  ADD COLUMN scoring_mode VARCHAR(64) NOT NULL DEFAULT 'single_realtime_hidden',
  ADD COLUMN leaderboard_rule VARCHAR(64) NOT NULL DEFAULT 'best_per_user',
  ADD COLUMN evaluation_policy VARCHAR(64) NOT NULL DEFAULT 'canonical_test_first';
