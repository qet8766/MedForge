from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID


def _env_bool(name: str, default: str) -> bool:
    raw = os.getenv(name, default).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_optional_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _env_optional_str(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    return value if value else default


def _default_cookie_domain() -> str:
    domain = os.getenv("DOMAIN", "").strip().lower()
    if not domain or domain in {"localhost", "127.0.0.1"}:
        return ""
    return f".medforge.{domain}"


def _default_cors_origins() -> tuple[str, ...]:
    domain = os.getenv("DOMAIN", "").strip().lower()
    origins = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
    if domain:
        origins.update(
            {
                f"http://medforge.{domain}",
                f"https://medforge.{domain}",
                f"http://api.medforge.{domain}",
                f"https://api.medforge.{domain}",
            }
        )
    return tuple(sorted(origins))


@dataclass(frozen=True)
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "MedForge API"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./medforge.db"))
    domain: str = field(default_factory=lambda: os.getenv("DOMAIN", "example.com").strip().lower())
    pack_image: str = field(
        default_factory=lambda: os.getenv("PACK_IMAGE", "").strip()
    )
    session_secret: str = field(default_factory=lambda: os.getenv("SESSION_SECRET", "dev-session-secret").strip())
    competitions_data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("COMPETITIONS_DATA_DIR", "data/competitions"))
    )
    submissions_dir: Path = field(default_factory=lambda: Path(os.getenv("SUBMISSIONS_DIR", "data/submissions")))
    default_user_id: UUID = field(
        default_factory=lambda: UUID(os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001"))
    )
    auto_score_on_submit: bool = field(default_factory=lambda: _env_bool("AUTO_SCORE_ON_SUBMIT", "true"))
    allow_legacy_header_auth: bool = field(default_factory=lambda: _env_bool("ALLOW_LEGACY_HEADER_AUTH", "false"))
    require_user_header: bool = field(default_factory=lambda: _env_bool("REQUIRE_USER_HEADER", "false"))
    submission_upload_max_bytes: int = field(
        default_factory=lambda: max(_env_int("SUBMISSION_UPLOAD_MAX_BYTES", 10 * 1024 * 1024), 1)
    )
    auth_idle_ttl_seconds: int = field(default_factory=lambda: _env_int("AUTH_IDLE_TTL_SECONDS", 604800))
    auth_max_ttl_seconds: int = field(default_factory=lambda: _env_int("AUTH_MAX_TTL_SECONDS", 2592000))
    cookie_name: str = field(default_factory=lambda: os.getenv("COOKIE_NAME", "medforge_session").strip())
    cookie_domain: str = field(default_factory=lambda: os.getenv("COOKIE_DOMAIN", _default_cookie_domain()).strip())
    cookie_secure: bool = field(default_factory=lambda: _env_bool("COOKIE_SECURE", "true"))
    cookie_samesite: str = field(default_factory=lambda: os.getenv("COOKIE_SAMESITE", "lax").strip().lower())
    cors_origins: tuple[str, ...] = field(default_factory=_default_cors_origins)
    admin_api_token: str = field(default_factory=lambda: os.getenv("ADMIN_API_TOKEN", "").strip())
    public_sessions_network: str = field(
        default_factory=lambda: os.getenv("PUBLIC_SESSIONS_NETWORK", "medforge-public-sessions").strip()
    )
    workspace_zfs_root: str = field(
        default_factory=lambda: os.getenv("WORKSPACE_ZFS_ROOT", "tank/medforge/workspaces").strip()
    )
    session_allocation_max_retries: int = field(default_factory=lambda: max(_env_int("SESSION_ALLOCATION_MAX_RETRIES", 3), 1))
    session_container_start_timeout_seconds: int = field(
        default_factory=lambda: max(_env_int("SESSION_CONTAINER_START_TIMEOUT_SECONDS", 30), 1)
    )
    session_container_stop_timeout_seconds: int = field(
        default_factory=lambda: max(_env_int("SESSION_CONTAINER_STOP_TIMEOUT_SECONDS", 30), 1)
    )
    session_workspace_quota_gb: int | None = field(default_factory=lambda: _env_optional_int("SESSION_WORKSPACE_QUOTA_GB"))
    session_runtime_mode: str = field(default_factory=lambda: os.getenv("SESSION_RUNTIME_MODE", "docker").strip().lower())
    session_runtime_use_sudo: bool = field(default_factory=lambda: _env_bool("SESSION_RUNTIME_USE_SUDO", "false"))
    session_recovery_enabled: bool = field(default_factory=lambda: _env_bool("SESSION_RECOVERY_ENABLED", "true"))
    session_poll_interval_seconds: int = field(default_factory=lambda: max(_env_int("SESSION_POLL_INTERVAL_SECONDS", 30), 1))
    session_poll_backoff_max_seconds: int = field(
        default_factory=lambda: max(_env_int("SESSION_POLL_BACKOFF_MAX_SECONDS", 300), 1)
    )
    # Container resource limits.
    session_cpu_shares: int = field(default_factory=lambda: _env_int("SESSION_CPU_SHARES", 1024))
    session_cpu_limit: int | None = field(default_factory=lambda: _env_optional_int("SESSION_CPU_LIMIT"))
    session_mem_limit: str | None = field(default_factory=lambda: _env_optional_str("SESSION_MEM_LIMIT", "64g"))
    session_mem_reservation: str | None = field(default_factory=lambda: _env_optional_str("SESSION_MEM_RESERVATION", "8g"))
    session_shm_size: str | None = field(default_factory=lambda: _env_optional_str("SESSION_SHM_SIZE", "4g"))
    session_pids_limit: int | None = field(default_factory=lambda: _env_optional_int("SESSION_PIDS_LIMIT"))


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS
