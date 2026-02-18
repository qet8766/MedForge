from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlmodel import Session, select

from app.api_contract import ApiEnvelope, envelope
from app.database import get_session
from app.models import Competition, SessionRecord, Submission, User
from app.schemas import (
    GpuStatus,
    PlatformStats,
    SessionSummary,
    StatusResponse,
    StorageInfo,
    SystemInfo,
)
from app.session_repo import ACTIVE_SESSION_STATUSES
from app.system_metrics import metrics_collector

router = APIRouter(tags=["status"])

_BYTES_PER_GIB = 1024**3


@router.get("/status", response_model=ApiEnvelope[StatusResponse])
def get_status(request: Request, session: Session = Depends(get_session)) -> ApiEnvelope[StatusResponse]:
    gpu_metrics = metrics_collector.get_gpu_metrics()
    sys_metrics = metrics_collector.get_system_metrics()
    zfs_metrics = metrics_collector.get_zfs_metrics()

    # Active sessions and their allocated GPU IDs
    active_rows = session.exec(
        select(SessionRecord.gpu_id, SessionRecord.status).where(
            SessionRecord.status.in_(ACTIVE_SESSION_STATUSES)  # type: ignore[union-attr]
        )
    ).all()
    allocated_gpu_ids: list[int] = []
    gpu_session_map: dict[int, str] = {}
    for gpu_id, sess_status in active_rows:
        allocated_gpu_ids.append(gpu_id)
        gpu_session_map[gpu_id] = sess_status.value if hasattr(sess_status, "value") else str(sess_status)

    # Platform stats
    total_users = session.exec(select(func.count()).select_from(User)).one()
    total_competitions = session.exec(select(func.count()).select_from(Competition)).one()
    total_submissions = session.exec(select(func.count()).select_from(Submission)).one()

    # Build GPU status list
    gpus = [
        GpuStatus(
            id=g.index,
            name=g.name,
            memory_total_mib=g.memory_total_mib,
            memory_used_mib=g.memory_used_mib,
            utilization_percent=g.utilization_percent,
            temperature_celsius=g.temperature_celsius,
            power_draw_watts=g.power_draw_watts,
            power_limit_watts=g.power_limit_watts,
            session_status=gpu_session_map.get(g.index),
        )
        for g in gpu_metrics
    ]

    system = SystemInfo(
        hostname=sys_metrics.hostname,
        cpu_model=sys_metrics.cpu_model,
        cpu_count=sys_metrics.cpu_count,
        cpu_cores=sys_metrics.cpu_cores,
        cpu_usage_percent=sys_metrics.cpu_usage_percent,
        ram_total_gib=round(sys_metrics.ram_total_bytes / _BYTES_PER_GIB, 1),
        ram_used_gib=round(sys_metrics.ram_used_bytes / _BYTES_PER_GIB, 1),
        ram_usage_percent=sys_metrics.ram_usage_percent,
        uptime_seconds=sys_metrics.uptime_seconds,
    )

    if zfs_metrics is not None:
        total_bytes = zfs_metrics.total_bytes
        used_bytes = zfs_metrics.used_bytes
        storage = StorageInfo(
            pool_name=zfs_metrics.pool_name,
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            free_bytes=zfs_metrics.free_bytes,
            usage_percent=round((used_bytes / total_bytes * 100) if total_bytes > 0 else 0.0, 1),
            health=zfs_metrics.health,
        )
    else:
        storage = StorageInfo(
            pool_name="tank",
            total_bytes=0,
            used_bytes=0,
            free_bytes=0,
            usage_percent=0.0,
            health="UNKNOWN",
        )

    sessions = SessionSummary(
        active_sessions=len(active_rows),
        total_gpus=len(gpus) if gpus else 7,
        gpus_in_use=len(allocated_gpu_ids),
        allocated_gpu_ids=sorted(allocated_gpu_ids),
    )

    platform = PlatformStats(
        total_users=total_users,
        total_competitions=total_competitions,
        total_submissions=total_submissions,
    )

    health_status: str = "ok"
    if zfs_metrics is not None and zfs_metrics.health != "ONLINE":
        health_status = "degraded"

    return envelope(
        request,
        StatusResponse(
            gpus=gpus,
            system=system,
            storage=storage,
            sessions=sessions,
            platform=platform,
            health_status=health_status,  # type: ignore[arg-type]
        ),
    )
