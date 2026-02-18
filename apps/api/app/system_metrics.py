from __future__ import annotations

import platform
import subprocess
import threading
import time
from dataclasses import dataclass

import psutil
import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GpuMetrics:
    index: int
    name: str
    memory_total_mib: int
    memory_used_mib: int
    utilization_percent: int
    temperature_celsius: int
    power_draw_watts: float
    power_limit_watts: float


@dataclass(frozen=True)
class SystemMetrics:
    hostname: str
    cpu_model: str
    cpu_cores: int
    cpu_count: int
    cpu_usage_percent: float
    ram_total_bytes: int
    ram_used_bytes: int
    ram_usage_percent: float
    uptime_seconds: int


@dataclass(frozen=True)
class ZfsPoolMetrics:
    pool_name: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    health: str


@dataclass
class _CachedValue[T]:
    value: T | None = None
    timestamp: float = 0.0


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._gpu_cache: _CachedValue[list[GpuMetrics]] = _CachedValue()
        self._system_cache: _CachedValue[SystemMetrics] = _CachedValue()
        self._zfs_cache: _CachedValue[ZfsPoolMetrics] = _CachedValue()
        self._static_cpu_model: str | None = None
        self._static_hostname: str | None = None

    def warmup(self) -> None:
        """Call once at startup to prime psutil CPU counter."""
        psutil.cpu_percent(interval=None)

    def _get_cpu_model(self) -> str:
        if self._static_cpu_model is not None:
            return self._static_cpu_model
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        model = line.split(":", 1)[1].strip()
                        self._static_cpu_model = model
                        return model
        except OSError:
            pass
        self._static_cpu_model = "Unknown CPU"
        return self._static_cpu_model

    def _get_hostname(self) -> str:
        if self._static_hostname is not None:
            return self._static_hostname
        self._static_hostname = platform.node() or "medforge"
        return self._static_hostname

    def _get_uptime_seconds(self) -> int:
        try:
            with open("/proc/uptime") as f:
                return int(float(f.readline().split()[0]))
        except (OSError, ValueError, IndexError):
            return 0

    def get_gpu_metrics(self, ttl: float = 5.0) -> list[GpuMetrics]:
        now = time.monotonic()
        with self._lock:
            if self._gpu_cache.value is not None and (now - self._gpu_cache.timestamp) < ttl:
                return self._gpu_cache.value

        gpus = self._collect_gpu_metrics()
        with self._lock:
            self._gpu_cache = _CachedValue(value=gpus, timestamp=time.monotonic())
        return gpus

    def get_system_metrics(self, ttl: float = 5.0) -> SystemMetrics:
        now = time.monotonic()
        with self._lock:
            if self._system_cache.value is not None and (now - self._system_cache.timestamp) < ttl:
                return self._system_cache.value

        metrics = self._collect_system_metrics()
        with self._lock:
            self._system_cache = _CachedValue(value=metrics, timestamp=time.monotonic())
        return metrics

    def get_zfs_metrics(self, ttl: float = 10.0) -> ZfsPoolMetrics | None:
        now = time.monotonic()
        with self._lock:
            if self._zfs_cache.value is not None and (now - self._zfs_cache.timestamp) < ttl:
                return self._zfs_cache.value

        pool = self._collect_zfs_metrics()
        if pool is not None:
            with self._lock:
                self._zfs_cache = _CachedValue(value=pool, timestamp=time.monotonic())
        return pool

    def _collect_gpu_metrics(self) -> list[GpuMetrics]:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw,power.limit",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.warning("nvidia_smi.failed", returncode=result.returncode, stderr=result.stderr.strip())
                return []

            gpus: list[GpuMetrics] = []
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 8:
                    continue
                gpus.append(
                    GpuMetrics(
                        index=int(parts[0]),
                        name=parts[1],
                        memory_total_mib=int(float(parts[2])),
                        memory_used_mib=int(float(parts[3])),
                        utilization_percent=int(float(parts[4])),
                        temperature_celsius=int(float(parts[5])),
                        power_draw_watts=round(float(parts[6]), 1),
                        power_limit_watts=round(float(parts[7]), 1),
                    )
                )
            return gpus
        except FileNotFoundError:
            logger.debug("nvidia_smi.not_found")
            return []
        except subprocess.TimeoutExpired:
            logger.warning("nvidia_smi.timeout")
            return []
        except Exception as exc:
            logger.warning("nvidia_smi.error", error=str(exc))
            return []

    def _collect_system_metrics(self) -> SystemMetrics:
        mem = psutil.virtual_memory()
        return SystemMetrics(
            hostname=self._get_hostname(),
            cpu_model=self._get_cpu_model(),
            cpu_cores=psutil.cpu_count(logical=False) or 1,
            cpu_count=psutil.cpu_count(logical=True) or 1,
            cpu_usage_percent=round(psutil.cpu_percent(interval=None), 1),
            ram_total_bytes=mem.total,
            ram_used_bytes=mem.used,
            ram_usage_percent=round(mem.percent, 1),
            uptime_seconds=self._get_uptime_seconds(),
        )

    def _collect_zfs_metrics(self) -> ZfsPoolMetrics | None:
        try:
            result = subprocess.run(
                ["zpool", "list", "-Hp", "-o", "name,size,alloc,free,health", "tank"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.warning("zpool.failed", returncode=result.returncode, stderr=result.stderr.strip())
                return None

            line = result.stdout.strip()
            if not line:
                return None

            parts = line.split("\t")
            if len(parts) < 5:
                return None

            return ZfsPoolMetrics(
                pool_name=parts[0],
                total_bytes=int(parts[1]),
                used_bytes=int(parts[2]),
                free_bytes=int(parts[3]),
                health=parts[4],
            )
        except FileNotFoundError:
            logger.debug("zpool.not_found")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("zpool.timeout")
            return None
        except Exception as exc:
            logger.warning("zpool.error", error=str(exc))
            return None


metrics_collector = MetricsCollector()
