-- MedForge alpha competition schema.
-- Canonical names intentionally avoid public/private score naming ambiguity.

CREATE TABLE IF NOT EXISTS datasets (
  id CHAR(36) PRIMARY KEY,
  slug VARCHAR(120) NOT NULL UNIQUE,
  title VARCHAR(255) NOT NULL,
  source VARCHAR(120) NOT NULL,
  license VARCHAR(255) NOT NULL,
  storage_path VARCHAR(512) NOT NULL,
  bytes BIGINT NOT NULL DEFAULT 0,
  checksum VARCHAR(128) NOT NULL,
  created_at DATETIME(6) NOT NULL
);

CREATE TABLE IF NOT EXISTS competitions (
  id CHAR(36) PRIMARY KEY,
  slug VARCHAR(120) NOT NULL UNIQUE,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  competition_tier ENUM('PUBLIC', 'PRIVATE') NOT NULL,
  status ENUM('active', 'inactive') NOT NULL,
  is_permanent BOOLEAN NOT NULL DEFAULT TRUE,
  metric VARCHAR(64) NOT NULL,
  higher_is_better BOOLEAN NOT NULL DEFAULT TRUE,
  submission_cap_per_day INT NOT NULL DEFAULT 10,
  dataset_id CHAR(36) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_competitions_dataset
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);

CREATE TABLE IF NOT EXISTS submissions (
  id CHAR(36) PRIMARY KEY,
  competition_id CHAR(36) NOT NULL,
  user_id CHAR(36) NOT NULL,
  filename VARCHAR(255) NOT NULL,
  artifact_path VARCHAR(512) NOT NULL,
  artifact_sha256 VARCHAR(128) NOT NULL,
  row_count INT NOT NULL DEFAULT 0,
  score_status ENUM('queued', 'scoring', 'scored', 'failed') NOT NULL,
  leaderboard_score DOUBLE NULL,
  score_error VARCHAR(2000) NULL,
  scorer_version VARCHAR(64) NULL,
  evaluation_split_version VARCHAR(64) NULL,
  created_at DATETIME(6) NOT NULL,
  scored_at DATETIME(6) NULL,
  INDEX ix_submissions_competition_created (competition_id, created_at),
  INDEX ix_submissions_competition_status (competition_id, score_status),
  CONSTRAINT fk_submissions_competition
    FOREIGN KEY (competition_id) REFERENCES competitions(id)
);
