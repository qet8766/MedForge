from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlmodel import Session

from app.config import Settings
from app.deps import AuthPrincipal
from app.models import Exposure, Role, SessionRecord, SessionStatus
from app.schemas import SessionActionResponse, SessionCreateRequest, SessionCreateResponse, SessionRead
from app.session_repo import (
    allocate_starting_session,
    finalize_error,
    finalize_running,
    get_or_create_principal_user,
    get_session_row,
    mark_session_stopping,
    resolve_pack,
)
from app.session_runtime import (
    SessionResourceLimits,
    SessionStartRequest,
    WorkspaceProvisionRequest,
    get_session_runtime,
)

logger = structlog.get_logger(__name__)


def create_session_for_principal(
    *,
    payload: SessionCreateRequest,
    exposure: Exposure,
    principal: AuthPrincipal,
    session: Session,
    settings: Settings,
) -> SessionCreateResponse:
    user = get_or_create_principal_user(session, principal)
    pack = resolve_pack(session, pack_id=payload.pack_id, exposure=exposure)

    row = allocate_starting_session(
        session,
        user_id=user.id,
        exposure=exposure,
        pack_id=pack.id,
        workspace_zfs_root=settings.workspace_zfs_root,
        max_retries=settings.session_allocation_max_retries,
    )

    runtime = get_session_runtime(settings)
    try:
        runtime.provision_workspace(
            WorkspaceProvisionRequest(
                workspace_zfs=row.workspace_zfs,
                uid=1000,
                gid=1000,
                quota_gb=settings.session_workspace_quota_gb,
            )
        )
        start_result = runtime.start_session(
            SessionStartRequest(
                session_id=row.id,
                user_id=row.user_id,
                exposure=row.exposure.value,
                slug=row.slug,
                gpu_id=row.gpu_id,
                workspace_zfs=row.workspace_zfs,
                pack_image_ref=pack.image_ref,
                sessions_network=(
                    settings.internal_sessions_network
                    if row.exposure == Exposure.INTERNAL
                    else settings.external_sessions_network
                ),
                start_timeout_seconds=settings.session_container_start_timeout_seconds,
                resource_limits=SessionResourceLimits(
                    cpu_shares=settings.session_cpu_shares,
                    cpu_limit=settings.session_cpu_limit,
                    mem_limit=settings.session_mem_limit,
                    mem_reservation=settings.session_mem_reservation,
                    shm_size=settings.session_shm_size,
                    pids_limit=settings.session_pids_limit,
                ),
            )
        )
        row = finalize_running(session, row=row, container_id=start_result.container_id)
    except Exception as exc:
        row = finalize_error(session, row=row, error_message=f"create failed: {exc}")
        logger.error(
            "session.start_failed",
            session_id=str(row.id),
            user_id=str(row.user_id),
            slug=row.slug,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start session runtime.",
        ) from exc

    logger.info(
        "session.start",
        session_id=str(row.id),
        user_id=str(row.user_id),
        exposure=row.exposure.value,
        gpu_id=row.gpu_id,
        pack_id=str(row.pack_id),
        slug=row.slug,
    )
    return SessionCreateResponse(message="Session started.", session=SessionRead.model_validate(row))


def _get_owned_or_admin_session(
    *,
    session: Session,
    session_id: UUID,
    principal: AuthPrincipal,
) -> SessionRecord:
    row = get_session_row(session, session_id=session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if principal.role != Role.ADMIN and row.user_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session access denied.")
    return row


def get_session_for_principal(
    *,
    session_id: UUID,
    principal: AuthPrincipal,
    session: Session,
    exposure: Exposure | None = None,
) -> SessionRead:
    row = _get_owned_or_admin_session(session=session, session_id=session_id, principal=principal)
    if exposure is not None and row.exposure != exposure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return SessionRead.model_validate(row)


def stop_session_for_principal(
    *,
    session_id: UUID,
    principal: AuthPrincipal,
    session: Session,
    exposure: Exposure | None = None,
) -> SessionActionResponse:
    row = _get_owned_or_admin_session(session=session, session_id=session_id, principal=principal)
    if exposure is not None and row.exposure != exposure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if row.status in {SessionStatus.STOPPED, SessionStatus.ERROR}:
        return SessionActionResponse(message="Session already terminal.")

    if row.status != SessionStatus.STOPPING:
        row = mark_session_stopping(session, row=row)
    return SessionActionResponse(message="Session stop requested.")
