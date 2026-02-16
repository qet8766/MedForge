from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlmodel import Session

from app.config import Settings
from app.deps import AuthPrincipal
from app.models import Role, SessionRecord, SessionStatus, Tier
from app.schemas import SessionCreateRequest, SessionCreateResponse, SessionRead, SessionStopResponse
from app.session_recovery import complete_stopping_session
from app.session_repo import (
    allocate_starting_session,
    finalize_error,
    finalize_running,
    get_or_create_principal_user,
    get_session_row,
    mark_session_stopping,
    resolve_pack,
)
from app.session_runtime import SessionRuntimeError, get_session_runtime

logger = structlog.get_logger(__name__)


def _as_session_read(row: SessionRecord) -> SessionRead:
    return SessionRead(
        id=row.id,
        user_id=row.user_id,
        tier=row.tier,
        pack_id=row.pack_id,
        status=row.status,
        container_id=row.container_id,
        gpu_id=row.gpu_id,
        slug=row.slug,
        workspace_zfs=row.workspace_zfs,
        created_at=row.created_at,
        started_at=row.started_at,
        stopped_at=row.stopped_at,
        error_message=row.error_message,
    )


def create_session_for_principal(
    *,
    payload: SessionCreateRequest,
    principal: AuthPrincipal,
    session: Session,
    settings: Settings,
) -> SessionCreateResponse:
    if payload.tier == "PRIVATE":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PRIVATE tier is not available yet.",
        )

    tier = Tier(payload.tier)
    user = get_or_create_principal_user(session, principal)
    pack = resolve_pack(session, pack_id=payload.pack_id, tier=tier)

    row = allocate_starting_session(
        session,
        user_id=user.id,
        tier=tier,
        pack_id=pack.id,
        workspace_zfs_root=settings.workspace_zfs_root,
        max_retries=settings.session_allocation_max_retries,
    )

    runtime = get_session_runtime(settings)
    try:
        runtime.ensure_workspace_dataset(
            row.workspace_zfs,
            uid=1000,
            gid=1000,
            quota_gb=settings.session_workspace_quota_gb,
        )
        container_id = runtime.start_session_container(row, pack)
        row = finalize_running(session, row=row, container_id=container_id)
    except SessionRuntimeError as exc:
        row = finalize_error(session, row=row, error_message=f"create failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start session runtime.",
        ) from exc
    except Exception as exc:
        row = finalize_error(session, row=row, error_message=f"create failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start session runtime.",
        ) from exc

    logger.info(
        "session.start",
        session_id=str(row.id),
        user_id=str(row.user_id),
        tier=row.tier.value,
        gpu_id=row.gpu_id,
        pack_id=str(row.pack_id),
        slug=row.slug,
    )
    return SessionCreateResponse(detail="Session started.", session=_as_session_read(row))


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


def stop_session_for_principal(
    *,
    session_id: UUID,
    principal: AuthPrincipal,
    session: Session,
    settings: Settings,
) -> SessionStopResponse:
    row = _get_owned_or_admin_session(session=session, session_id=session_id, principal=principal)
    if row.status in {SessionStatus.STOPPED, SessionStatus.ERROR}:
        return SessionStopResponse(detail="Session already terminal.", session=_as_session_read(row))

    row = mark_session_stopping(session, row=row)
    runtime = get_session_runtime(settings)
    reason = "admin" if principal.role == Role.ADMIN and row.user_id != principal.user_id else "user"

    row = complete_stopping_session(
        session,
        row=row,
        settings=settings,
        runtime=runtime,
        success_reason=reason,
    )
    if row.status == SessionStatus.STOPPED:
        return SessionStopResponse(detail="Session stopped.", session=_as_session_read(row))
    return SessionStopResponse(detail="Session stop failed; marked error.", session=_as_session_read(row))
