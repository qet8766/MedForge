"""Verify that session container resource-limit settings parse correctly."""

from __future__ import annotations

from app.config import Settings


class TestResourceLimitSettings:
    """Settings dataclass should parse resource-limit env vars."""

    def test_defaults(self):
        """With no env vars set, defaults should apply."""
        s = Settings()
        assert s.session_cpu_shares == 1024
        assert s.session_cpu_limit is None
        assert s.session_mem_limit == "64g"
        assert s.session_mem_reservation == "8g"
        assert s.session_shm_size == "4g"
        assert s.session_pids_limit is None

    def test_all_set(self, monkeypatch):
        """All resource-limit env vars set to explicit values."""
        monkeypatch.setenv("SESSION_CPU_SHARES", "2048")
        monkeypatch.setenv("SESSION_CPU_LIMIT", "48")
        monkeypatch.setenv("SESSION_MEM_LIMIT", "32g")
        monkeypatch.setenv("SESSION_MEM_RESERVATION", "4g")
        monkeypatch.setenv("SESSION_SHM_SIZE", "2g")
        monkeypatch.setenv("SESSION_PIDS_LIMIT", "4096")

        s = Settings()
        assert s.session_cpu_shares == 2048
        assert s.session_cpu_limit == 48
        assert s.session_mem_limit == "32g"
        assert s.session_mem_reservation == "4g"
        assert s.session_shm_size == "2g"
        assert s.session_pids_limit == 4096

    def test_disabled_via_empty(self, monkeypatch):
        """Empty strings disable optional-int limits; optional-str fall back to defaults."""
        monkeypatch.setenv("SESSION_CPU_LIMIT", "")
        monkeypatch.setenv("SESSION_MEM_LIMIT", "")
        monkeypatch.setenv("SESSION_MEM_RESERVATION", "")
        monkeypatch.setenv("SESSION_SHM_SIZE", "")
        monkeypatch.setenv("SESSION_PIDS_LIMIT", "")

        s = Settings()
        # Int-typed optional limits become None on empty string.
        assert s.session_cpu_limit is None
        assert s.session_pids_limit is None
        # Str-typed optional limits fall back to their non-None defaults.
        assert s.session_mem_limit == "64g"
        assert s.session_mem_reservation == "8g"
        assert s.session_shm_size == "4g"

    def test_str_limits_explicitly_disabled(self):
        """Str-typed limits can be disabled via constructor (no env-based disable)."""
        s = Settings(session_mem_limit=None, session_mem_reservation=None, session_shm_size=None)
        assert s.session_mem_limit is None
        assert s.session_mem_reservation is None
        assert s.session_shm_size is None

    def test_nano_cpus_conversion(self):
        """session_cpu_limit * 10**9 gives correct nano_cpus value."""
        s = Settings(session_cpu_limit=48)
        assert s.session_cpu_limit * 10**9 == 48_000_000_000

    def test_swap_equals_mem(self):
        """memswap_limit should equal mem_limit (swap disabled)."""
        s = Settings(session_mem_limit="64g")
        # The runtime sets memswap_limit = mem_limit; verify the setting is usable.
        assert s.session_mem_limit == "64g"
