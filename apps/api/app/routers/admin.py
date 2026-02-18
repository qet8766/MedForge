from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.api_contract import ApiEnvelope, envelope
from app.database import get_session
from app.deps import AuthPrincipal, get_current_user, require_admin_access, require_allowed_origin
from app.models import Exposure, SessionRecord, SessionStatus, User
from app.pagination import decode_offset_cursor, encode_offset_cursor, validate_limit
from app.schemas import (
    SessionRead,
    UserAdminRead,
    UserAdminUpdateRequest,
)
from app.session_repo import ACTIVE_SESSION_STATUSES
from app.util import commit_and_refresh, parse_enum_filter

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_access)])


def _active_session_count(session: Session, *, user_id: UUID) -> int:
    status_col = cast(Any, SessionRecord.status)
    statement = (
        select(func.count())
        .select_from(SessionRecord)
        .where(SessionRecord.user_id == user_id)
        .where(status_col.in_(ACTIVE_SESSION_STATUSES))
    )
    return int(session.exec(statement).one())


def _user_admin_read(user: User, *, active_count: int) -> UserAdminRead:
    return UserAdminRead(
        user_id=user.id,
        email=user.email,
        role=user.role,
        can_use_internal=user.can_use_internal,
        max_concurrent_sessions=user.max_concurrent_sessions,
        created_at=user.created_at,
        active_session_count=active_count,
    )


@router.get("/users", response_model=ApiEnvelope[list[UserAdminRead]])
def list_users(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    cursor: str | None = Query(default=None),
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiEnvelope[list[UserAdminRead]]:
    validated_limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)

    statement = select(User).order_by(cast(Any, User.created_at).desc())
    total_rows = list(session.exec(statement).all())
    page = total_rows[offset : offset + validated_limit]

    has_more = offset + validated_limit < len(total_rows)
    next_cursor = encode_offset_cursor(offset + validated_limit) if has_more else None

    results: list[UserAdminRead] = []
    for user in page:
        active_count = _active_session_count(session, user_id=user.id)
        results.append(_user_admin_read(user, active_count=active_count))

    return envelope(
        request,
        results,
        limit=validated_limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.patch("/users/{user_id}", response_model=ApiEnvelope[UserAdminRead])
def update_user(
    request: Request,
    user_id: UUID = Path(),
    payload: UserAdminUpdateRequest = ...,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    _origin_guard: None = Depends(require_allowed_origin),
) -> ApiEnvelope[UserAdminRead]:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if payload.role is not None:
        user.role = payload.role
    if payload.can_use_internal is not None:
        user.can_use_internal = payload.can_use_internal
    if payload.max_concurrent_sessions is not None:
        user.max_concurrent_sessions = payload.max_concurrent_sessions

    commit_and_refresh(session, user)

    active_count = _active_session_count(session, user_id=user.id)

    return envelope(
        request,
        _user_admin_read(user, active_count=active_count),
    )


@router.get("/sessions", response_model=ApiEnvelope[list[SessionRead]])
def list_all_sessions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    cursor: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    exposure: str | None = Query(default=None),
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiEnvelope[list[SessionRead]]:
    validated_limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)

    statement = select(SessionRecord)

    valid_statuses = parse_enum_filter(status_filter, SessionStatus)
    if valid_statuses:
        status_col = cast(Any, SessionRecord.status)
        statement = statement.where(status_col.in_(valid_statuses))

    if exposure:
        try:
            exp = Exposure(exposure.upper())
            statement = statement.where(SessionRecord.exposure == exp)
        except ValueError:
            pass

    created_col = cast(Any, SessionRecord.created_at)
    statement = statement.order_by(created_col.desc())

    all_rows = list(session.exec(statement).all())
    page = all_rows[offset : offset + validated_limit]

    has_more = offset + validated_limit < len(all_rows)
    next_cursor = encode_offset_cursor(offset + validated_limit) if has_more else None

    results = [SessionRead.model_validate(row) for row in page]

    return envelope(
        request,
        results,
        limit=validated_limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )
