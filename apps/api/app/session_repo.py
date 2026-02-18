from __future__ import annotations

import base64
import secrets
import uuid
from collections.abc import Iterable
from typing import Any, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.deps import AuthPrincipal
from app.models import Exposure, GpuDevice, Pack, PackExposure, Role, SessionRecord, SessionStatus, User
from app.seed import DEFAULT_PACK_ID
from app.util import utcnow

ACTIVE_SESSION_STATUSES: tuple[SessionStatus, ...] = (
    SessionStatus.STARTING,
    SessionStatus.RUNNING,
    SessionStatus.STOPPING,
)


def _slug_token() -> str:
    encoded = base64.b32encode(secrets.token_bytes(8)).decode("ascii").lower().rstrip("=")
    return encoded[:8]


def _workspace_path(root: str, *, user_id: UUID, session_id: UUID) -> str:
    trimmed = root.strip().strip("/")
    if not trimmed:
        trimmed = "tank/medforge/workspaces"
    return f"{trimmed}/{user_id}/{session_id}"


def get_or_create_principal_user(session: Session, principal: AuthPrincipal) -> User:
    user = session.get(User, principal.user_id)
    if user is not None:
        return user

    if principal.source != "legacy_header":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found.",
        )

    legacy_email = f"legacy-{principal.user_id}@medforge.local"
    user = User(
        id=principal.user_id,
        email=legacy_email,
        password_hash="legacy-header-auth",
        role=Role.ADMIN if principal.role == Role.ADMIN else Role.USER,
        can_use_internal=principal.role == Role.ADMIN,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def resolve_pack(session: Session, *, pack_id: UUID | None, exposure: Exposure) -> Pack:
    selected_pack_id = pack_id or DEFAULT_PACK_ID
    pack = session.get(Pack, selected_pack_id)
    if pack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack not found.")
    if pack.deprecated_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected pack is deprecated.")

    if exposure == Exposure.EXTERNAL and pack.exposure == PackExposure.INTERNAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Selected pack does not support EXTERNAL exposure.",
        )
    if exposure == Exposure.INTERNAL and pack.exposure == PackExposure.EXTERNAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Selected pack does not support INTERNAL exposure.",
        )
    return pack


def _lock_user_for_allocation(session: Session, *, user_id: UUID) -> User | None:
    statement = select(User).where(User.id == user_id).with_for_update()
    return session.exec(statement).first()


def _count_active_sessions(session: Session, *, user_id: UUID) -> int:
    status_col = cast(Any, SessionRecord.status)
    statement = (
        select(func.count())
        .select_from(SessionRecord)
        .where(SessionRecord.user_id == user_id)
        .where(status_col.in_(ACTIVE_SESSION_STATUSES))
    )
    return int(session.exec(statement).one())


def _select_free_gpu(session: Session) -> int | None:
    status_col = cast(Any, SessionRecord.status)
    gpu_id_col = cast(Any, GpuDevice.id)
    enabled_col = cast(Any, GpuDevice.enabled)
    active_gpu_ids = select(SessionRecord.gpu_id).where(status_col.in_(ACTIVE_SESSION_STATUSES))
    statement = (
        select(gpu_id_col)
        .where(enabled_col.is_(True))
        .where(~gpu_id_col.in_(active_gpu_ids))
        .order_by(gpu_id_col)
        .with_for_update()
    )
    return cast(int | None, session.exec(statement).first())


def allocate_starting_session(
    session: Session,
    *,
    user_id: UUID,
    exposure: Exposure,
    pack_id: UUID,
    workspace_zfs_root: str,
    max_retries: int,
) -> SessionRecord:
    retries = max(max_retries, 1)

    for attempt in range(retries):
        try:
            user = _lock_user_for_allocation(session, user_id=user_id)
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

            active_count = _count_active_sessions(session, user_id=user.id)
            if active_count >= user.max_concurrent_sessions:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Concurrent session limit reached ({user.max_concurrent_sessions}).",
                )

            gpu_id = _select_free_gpu(session)
            if gpu_id is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No GPUs available.",
                )

            session_id = uuid.uuid4()
            row = SessionRecord(
                id=session_id,
                user_id=user.id,
                exposure=exposure,
                pack_id=pack_id,
                status=SessionStatus.STARTING,
                gpu_id=gpu_id,
                slug=_slug_token(),
                workspace_zfs=_workspace_path(workspace_zfs_root, user_id=user.id, session_id=session_id),
            )

            session.add(row)
            session.commit()
            session.refresh(row)
            return row
        except HTTPException:
            session.rollback()
            raise
        except IntegrityError as exc:
            session.rollback()
            if attempt + 1 < retries:
                continue
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session allocation conflict. Please retry.",
            ) from exc

    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session allocation failed.")


def mark_session_stopping(session: Session, *, row: SessionRecord) -> SessionRecord:
    row.status = SessionStatus.STOPPING
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def finalize_running(session: Session, *, row: SessionRecord, container_id: str) -> SessionRecord:
    row.status = SessionStatus.RUNNING
    row.container_id = container_id
    row.started_at = utcnow()
    row.error_message = None
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def finalize_stopped(session: Session, *, row: SessionRecord) -> SessionRecord:
    row.status = SessionStatus.STOPPED
    row.stopped_at = utcnow()
    row.error_message = None
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def finalize_error(session: Session, *, row: SessionRecord, error_message: str) -> SessionRecord:
    row.status = SessionStatus.ERROR
    row.stopped_at = utcnow()
    row.error_message = error_message[:2000]
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_session_row(session: Session, *, session_id: UUID) -> SessionRecord | None:
    return session.get(SessionRecord, session_id)


def list_sessions_for_user(
    session: Session,
    *,
    user_id: UUID,
    statuses: Iterable[SessionStatus] | None = None,
    exposure: Exposure | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[SessionRecord]:
    statement = select(SessionRecord).where(SessionRecord.user_id == user_id)
    if statuses is not None:
        status_col = cast(Any, SessionRecord.status)
        statement = statement.where(status_col.in_(tuple(statuses)))
    if exposure is not None:
        statement = statement.where(SessionRecord.exposure == exposure)
    created_col = cast(Any, SessionRecord.created_at)
    statement = statement.order_by(created_col.desc())
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.exec(statement).all())


def count_sessions_for_user(
    session: Session,
    *,
    user_id: UUID,
    statuses: Iterable[SessionStatus] | None = None,
    exposure: Exposure | None = None,
) -> int:
    statement = (
        select(func.count())
        .select_from(SessionRecord)
        .where(SessionRecord.user_id == user_id)
    )
    if statuses is not None:
        status_col = cast(Any, SessionRecord.status)
        statement = statement.where(status_col.in_(tuple(statuses)))
    if exposure is not None:
        statement = statement.where(SessionRecord.exposure == exposure)
    return int(session.exec(statement).one())
