from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Field-factory helpers - each returns a dataclass field() whose
# default_factory reads os.environ at instantiation time.
# Default-arg capture (_n=name, _d=default ...) prevents late-binding issues.
# ---------------------------------------------------------------------------

def _env(name: str, default: str, *, lower: bool = False) -> str:
    def _factory(_n: str = name, _d: str = default, _l: bool = lower) -> str:
        v = os.getenv(_n, _d).strip()
        return v.lower() if _l else v
    return field(default_factory=_factory)


def _env_bool(name: str, default: str) -> bool:
    def _factory(_n: str = name, _d: str = default) -> bool:
        return os.getenv(_n, _d).strip().lower() in {"1", "true", "yes", "on"}
    return field(default_factory=_factory)


def _env_int(name: str, default: int, *, min: int | None = None) -> int:
    def _factory(_n: str = name, _d: int = default, _m: int | None = min) -> int:
        raw = os.getenv(_n)
        if raw is None:
            v = _d
        else:
            try:
                v = int(raw.strip())
            except ValueError:
                v = _d
        return max(v, _m) if _m is not None else v
    return field(default_factory=_factory)

def _env_opt_int(name: str) -> int | None:
    def _factory(_n: str = name) -> int | None:
        raw = os.getenv(_n)
        if raw is None:
            return None
        value = raw.strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return field(default_factory=_factory)


def _env_opt_str(name: str, default: str | None = None) -> str | None:
    def _factory(_n: str = name, _d: str | None = default) -> str | None:
        raw = os.getenv(_n)
        if raw is None:
            return _d
        value = raw.strip()
        return value if value else _d
    return field(default_factory=_factory)


# ---------------------------------------------------------------------------
# Computed defaults that don't fit the one-liner helpers.
# ---------------------------------------------------------------------------

def _default_cookie_domain() -> str:
    domain = os.getenv("DOMAIN", "").strip().lower()
    if not domain or domain in {"localhost", "127.0.0.1"}:
        return ""
    return f".medforge.{domain}"


def _default_cors_origins() -> tuple[str, ...]:
    domain = os.getenv("DOMAIN", "").strip().lower()
    is_local = not domain or domain in {"localhost", "127.0.0.1"}
    origins: set[str] = set()
    if is_local:
        origins.update({"http://localhost:3000", "http://127.0.0.1:3000"})
    if domain:
        origins.update(
            f"{s}://{p}medforge.{domain}"
            for s in ("http", "https") for p in ("", "api.")
        )
    return tuple(sorted(origins))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    app_name: str = _env("APP_NAME", "MedForge API")
    database_url: str = _env("DATABASE_URL", "mysql+pymysql://medforge:medforge@localhost:3306/medforge")
    domain: str = _env("DOMAIN", "example.com", lower=True)
    pack_image: str = _env("PACK_IMAGE", "")
    session_secret: str = _env("SESSION_SECRET", "dev-session-secret")
    datasets_root: Path = field(
        default_factory=lambda: Path(
            os.getenv("MEDFORGE_DATASETS_ROOT", "/data/medforge/datasets").strip() or "/data/medforge/datasets"
        )
    )
    competitions_data_dir: Path = field(default_factory=lambda: Path(os.getenv("COMPETITIONS_DATA_DIR", "data/competitions")))
    submissions_dir: Path = field(default_factory=lambda: Path(os.getenv("SUBMISSIONS_DIR", "data/submissions")))
    auto_score_on_submit: bool = _env_bool("AUTO_SCORE_ON_SUBMIT", "true")
    submission_upload_max_bytes: int = _env_int("SUBMISSION_UPLOAD_MAX_BYTES", 10 * 1024 * 1024, min=1)
    auth_idle_ttl_seconds: int = _env_int("AUTH_IDLE_TTL_SECONDS", 604800)
    auth_max_ttl_seconds: int = _env_int("AUTH_MAX_TTL_SECONDS", 2592000)
    cookie_name: str = _env("COOKIE_NAME", "medforge_session")
    cookie_domain: str = field(default_factory=lambda: os.getenv("COOKIE_DOMAIN", _default_cookie_domain()).strip())
    cookie_secure: bool = _env_bool("COOKIE_SECURE", "true")
    cookie_samesite: str = _env("COOKIE_SAMESITE", "lax", lower=True)
    cors_origins: tuple[str, ...] = field(default_factory=_default_cors_origins)
    public_sessions_network: str = _env("PUBLIC_SESSIONS_NETWORK", "medforge-public-sessions")
    workspace_zfs_root: str = _env("WORKSPACE_ZFS_ROOT", "tank/medforge/workspaces")
    session_allocation_max_retries: int = _env_int("SESSION_ALLOCATION_MAX_RETRIES", 3, min=1)
    session_container_start_timeout_seconds: int = _env_int("SESSION_CONTAINER_START_TIMEOUT_SECONDS", 30, min=1)
    session_container_stop_timeout_seconds: int = _env_int("SESSION_CONTAINER_STOP_TIMEOUT_SECONDS", 30, min=1)
    session_workspace_quota_gb: int | None = _env_opt_int("SESSION_WORKSPACE_QUOTA_GB")
    session_runtime_mode: str = _env("SESSION_RUNTIME_MODE", "docker", lower=True)
    session_runtime_use_sudo: bool = _env_bool("SESSION_RUNTIME_USE_SUDO", "false")
    session_recovery_enabled: bool = _env_bool("SESSION_RECOVERY_ENABLED", "true")
    session_poll_interval_seconds: int = _env_int("SESSION_POLL_INTERVAL_SECONDS", 30, min=1)
    session_poll_backoff_max_seconds: int = _env_int("SESSION_POLL_BACKOFF_MAX_SECONDS", 300, min=1)
    # Container resource limits.
    session_cpu_shares: int = _env_int("SESSION_CPU_SHARES", 1024)
    session_cpu_limit: int | None = _env_opt_int("SESSION_CPU_LIMIT")
    session_mem_limit: str | None = _env_opt_str("SESSION_MEM_LIMIT", "64g")
    session_mem_reservation: str | None = _env_opt_str("SESSION_MEM_RESERVATION", "8g")
    session_shm_size: str | None = _env_opt_str("SESSION_SHM_SIZE", "4g")
    session_pids_limit: int | None = _env_opt_int("SESSION_PIDS_LIMIT")
    legacy_api_deprecation_enabled: bool = _env_bool("LEGACY_API_DEPRECATION_ENABLED", "true")
    legacy_api_sunset: str = _env("LEGACY_API_SUNSET", "Wed, 31 Dec 2026 23:59:59 GMT")
    legacy_api_deprecation_link: str = _env("LEGACY_API_DEPRECATION_LINK", "/docs/api-deprecations#legacy-api")


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS
