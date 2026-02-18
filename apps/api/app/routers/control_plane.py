from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlmodel import Session, select

from app.api_contract import ApiEnvelope, envelope
from app.config import Settings, get_settings
from app.database import get_session
from app.deps import AuthPrincipal, get_current_user, require_allowed_origin, require_internal_access
from app.models import Exposure, SessionRecord, SessionStatus, User
from app.pagination import decode_offset_cursor, encode_offset_cursor, validate_limit
from app.schemas import (
    MeResponse,
    MeUpdateRequest,
    SessionActionResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionCurrentResponse,
    SessionRead,
)
from app.security import hash_password, normalize_email, verify_password
from app.session_lifecycle import create_session_for_principal, get_session_for_principal, stop_session_for_principal
from app.session_repo import ACTIVE_SESSION_STATUSES, list_sessions_for_user
from app.util import commit_and_refresh, parse_enum_filter

router = APIRouter(tags=["control-plane"])


def _session_read_with_ssh_host(row: SessionRecord, settings: Settings) -> SessionRead:
    data = SessionRead.model_validate(row)
    data.ssh_host = settings.ssh_host
    return data


def _current_session_for_exposure(
    *,
    request: Request,
    principal: AuthPrincipal,
    session: Session,
    settings: Settings,
    exposure: Exposure,
) -> ApiEnvelope[SessionCurrentResponse]:
    active_rows = list_sessions_for_user(
        session,
        user_id=principal.user_id,
        statuses=ACTIVE_SESSION_STATUSES,
        exposure=exposure,
    )
    current = active_rows[0] if active_rows else None
    return envelope(
        request,
        SessionCurrentResponse(session=_session_read_with_ssh_host(current, settings) if current is not None else None),
    )


def _create_session_for_exposure(
    *,
    request: Request,
    payload: SessionCreateRequest,
    principal: AuthPrincipal,
    session: Session,
    settings: Settings,
    exposure: Exposure,
) -> ApiEnvelope[SessionCreateResponse]:
    result = create_session_for_principal(
        payload=payload,
        exposure=exposure,
        principal=principal,
        session=session,
        settings=settings,
    )
    return envelope(request, result)


@router.get("/me", response_model=ApiEnvelope[MeResponse])
def get_me(
    request: Request,
    principal: AuthPrincipal = Depends(get_current_user),
) -> ApiEnvelope[MeResponse]:
    return envelope(
        request,
        MeResponse(
            user_id=principal.user_id,
            role=principal.role,
            email=principal.email,
            can_use_internal=principal.can_use_internal,
            ssh_public_key=principal.ssh_public_key,
        ),
    )


@router.get("/external/sessions/current", response_model=ApiEnvelope[SessionCurrentResponse])
def get_current_external_session(
    request: Request,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiEnvelope[SessionCurrentResponse]:
    return _current_session_for_exposure(
        request=request,
        principal=principal,
        session=session,
        settings=settings,
        exposure=Exposure.EXTERNAL,
    )


@router.get("/internal/sessions/current", response_model=ApiEnvelope[SessionCurrentResponse])
def get_current_internal_session(
    request: Request,
    principal: AuthPrincipal = Depends(require_internal_access),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiEnvelope[SessionCurrentResponse]:
    return _current_session_for_exposure(
        request=request,
        principal=principal,
        session=session,
        settings=settings,
        exposure=Exposure.INTERNAL,
    )


@router.post(
    "/external/sessions", response_model=ApiEnvelope[SessionCreateResponse], status_code=status.HTTP_201_CREATED
)
def create_external_session(
    request: Request,
    payload: SessionCreateRequest,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _origin_guard: None = Depends(require_allowed_origin),
) -> ApiEnvelope[SessionCreateResponse]:
    return _create_session_for_exposure(
        request=request,
        payload=payload,
        principal=principal,
        session=session,
        settings=settings,
        exposure=Exposure.EXTERNAL,
    )


@router.post(
    "/internal/sessions", response_model=ApiEnvelope[SessionCreateResponse], status_code=status.HTTP_201_CREATED
)
def create_internal_session(
    request: Request,
    payload: SessionCreateRequest,
    principal: AuthPrincipal = Depends(require_internal_access),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _origin_guard: None = Depends(require_allowed_origin),
) -> ApiEnvelope[SessionCreateResponse]:
    return _create_session_for_exposure(
        request=request,
        payload=payload,
        principal=principal,
        session=session,
        settings=settings,
        exposure=Exposure.INTERNAL,
    )


@router.get("/external/sessions/{id}", response_model=ApiEnvelope[SessionRead])
def get_external_session(
    request: Request,
    session_id: UUID = Path(alias="id"),
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiEnvelope[SessionRead]:
    result = get_session_for_principal(
        session_id=session_id,
        principal=principal,
        session=session,
        exposure=Exposure.EXTERNAL,
    )
    result.ssh_host = settings.ssh_host
    return envelope(request, result)


@router.get("/internal/sessions/{id}", response_model=ApiEnvelope[SessionRead])
def get_internal_session(
    request: Request,
    session_id: UUID = Path(alias="id"),
    principal: AuthPrincipal = Depends(require_internal_access),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiEnvelope[SessionRead]:
    result = get_session_for_principal(
        session_id=session_id,
        principal=principal,
        session=session,
        exposure=Exposure.INTERNAL,
    )
    result.ssh_host = settings.ssh_host
    return envelope(request, result)


@router.post(
    "/external/sessions/{id}/stop",
    response_model=ApiEnvelope[SessionActionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def stop_external_session(
    request: Request,
    session_id: UUID = Path(alias="id"),
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    _origin_guard: None = Depends(require_allowed_origin),
) -> ApiEnvelope[SessionActionResponse]:
    result = stop_session_for_principal(
        session_id=session_id,
        principal=principal,
        session=session,
        exposure=Exposure.EXTERNAL,
    )
    return envelope(request, result)


@router.post(
    "/internal/sessions/{id}/stop",
    response_model=ApiEnvelope[SessionActionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def stop_internal_session(
    request: Request,
    session_id: UUID = Path(alias="id"),
    principal: AuthPrincipal = Depends(require_internal_access),
    session: Session = Depends(get_session),
    _origin_guard: None = Depends(require_allowed_origin),
) -> ApiEnvelope[SessionActionResponse]:
    result = stop_session_for_principal(
        session_id=session_id,
        principal=principal,
        session=session,
        exposure=Exposure.INTERNAL,
    )
    return envelope(request, result)


@router.patch("/me", response_model=ApiEnvelope[MeResponse])
def update_me(
    request: Request,
    payload: MeUpdateRequest,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    _origin_guard: None = Depends(require_allowed_origin),
) -> ApiEnvelope[MeResponse]:
    user = session.get(User, principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if payload.email is not None:
        normalized = normalize_email(payload.email)
        if normalized != user.email:
            existing = session.exec(select(User).where(User.email == normalized)).first()
            if existing is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use.")
            user.email = normalized

    if payload.new_password is not None:
        if payload.current_password is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Current password is required to set a new password.",
            )
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect.")
        user.password_hash = hash_password(payload.new_password)

    if payload.ssh_public_key is not None:
        trimmed = payload.ssh_public_key.strip()
        if trimmed == "":
            user.ssh_public_key = None
        else:
            _SSH_KEY_PREFIXES = ("ssh-rsa ", "ssh-ed25519 ", "ecdsa-sha2-", "sk-ssh-")
            if not trimmed.startswith(_SSH_KEY_PREFIXES):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid SSH public key format.",
                )
            user.ssh_public_key = trimmed

    commit_and_refresh(session, user)

    return envelope(
        request,
        MeResponse(
            user_id=user.id,
            role=user.role,
            email=user.email,
            can_use_internal=user.can_use_internal,
            ssh_public_key=user.ssh_public_key,
        ),
    )


@router.get("/external/sessions", response_model=ApiEnvelope[list[SessionRead]])
def list_external_sessions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=500),
    cursor: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiEnvelope[list[SessionRead]]:
    return _list_sessions_for_exposure(
        request=request,
        principal=principal,
        session=session,
        settings=settings,
        exposure=Exposure.EXTERNAL,
        limit=limit,
        cursor=cursor,
        status_filter=status_filter,
    )


@router.get("/internal/sessions", response_model=ApiEnvelope[list[SessionRead]])
def list_internal_sessions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=500),
    cursor: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    principal: AuthPrincipal = Depends(require_internal_access),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiEnvelope[list[SessionRead]]:
    return _list_sessions_for_exposure(
        request=request,
        principal=principal,
        session=session,
        settings=settings,
        exposure=Exposure.INTERNAL,
        limit=limit,
        cursor=cursor,
        status_filter=status_filter,
    )


def _list_sessions_for_exposure(
    *,
    request: Request,
    principal: AuthPrincipal,
    session: Session,
    settings: Settings,
    exposure: Exposure,
    limit: int,
    cursor: str | None,
    status_filter: str | None,
) -> ApiEnvelope[list[SessionRead]]:
    validated_limit = validate_limit(limit)
    offset = decode_offset_cursor(cursor)

    parsed_statuses = parse_enum_filter(status_filter, SessionStatus)
    statuses: tuple[SessionStatus, ...] | None = tuple(parsed_statuses) if parsed_statuses else None

    page = list_sessions_for_user(
        session,
        user_id=principal.user_id,
        statuses=statuses,
        exposure=exposure,
        limit=validated_limit + 1,
        offset=offset,
    )

    has_more = len(page) > validated_limit
    if has_more:
        page = page[:validated_limit]
    next_cursor = encode_offset_cursor(offset + validated_limit) if has_more else None

    results = [_session_read_with_ssh_host(row, settings) for row in page]

    return envelope(
        request,
        results,
        limit=validated_limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )
