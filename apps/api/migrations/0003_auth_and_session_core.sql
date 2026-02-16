-- Gate 2 foundation: auth and session control-plane schema.

CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,
  email VARCHAR(320) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('user', 'admin') NOT NULL DEFAULT 'user',
  max_concurrent_sessions INT NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL,
  CONSTRAINT ck_users_max_sessions_positive CHECK (max_concurrent_sessions > 0)
);

CREATE TABLE IF NOT EXISTS auth_sessions (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  token_hash VARCHAR(128) NOT NULL UNIQUE,
  created_at DATETIME(6) NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  revoked_at DATETIME(6) NULL,
  last_seen_at DATETIME(6) NULL,
  ip VARCHAR(64) NULL,
  user_agent VARCHAR(512) NULL,
  INDEX ix_auth_sessions_user_id (user_id),
  INDEX ix_auth_sessions_expires_at (expires_at),
  CONSTRAINT fk_auth_sessions_user
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS packs (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  tier ENUM('PUBLIC', 'PRIVATE', 'BOTH') NOT NULL,
  image_ref VARCHAR(255) NOT NULL,
  image_digest VARCHAR(255) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  deprecated_at DATETIME(6) NULL
);

CREATE TABLE IF NOT EXISTS gpu_devices (
  id INT PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS sessions (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  tier ENUM('PUBLIC', 'PRIVATE') NOT NULL,
  pack_id CHAR(36) NOT NULL,
  status ENUM('starting', 'running', 'stopping', 'stopped', 'error') NOT NULL,
  container_id VARCHAR(128) NULL,
  gpu_id INT NOT NULL,
  gpu_active TINYINT AS (
    CASE
      WHEN status IN ('starting', 'running', 'stopping') THEN 1
      ELSE NULL
    END
  ) STORED,
  slug CHAR(8) NOT NULL UNIQUE,
  workspace_zfs VARCHAR(255) NOT NULL UNIQUE,
  created_at DATETIME(6) NOT NULL,
  started_at DATETIME(6) NULL,
  stopped_at DATETIME(6) NULL,
  error_message VARCHAR(2000) NULL,
  INDEX ix_sessions_user_status (user_id, status),
  CONSTRAINT fk_sessions_user
    FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_sessions_pack
    FOREIGN KEY (pack_id) REFERENCES packs(id),
  CONSTRAINT fk_sessions_gpu
    FOREIGN KEY (gpu_id) REFERENCES gpu_devices(id),
  CONSTRAINT uq_sessions_gpu_active UNIQUE (gpu_id, gpu_active)
);
