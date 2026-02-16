from __future__ import annotations

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.api_contract import ApiEnvelope, envelope
from app.config import Settings, get_settings
from app.database import get_session
from app.deps import AuthPrincipal, get_current_user, require_allowed_origin
from app.models import Role, SessionRecord, SessionStatus
from app.schemas import (
    MeResponse,
    SessionActionResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionCurrentResponse,
    SessionRead,
)
from app.session_lifecycle import create_session_for_principal, stop_session_for_principal
from app.session_repo import ACTIVE_SESSION_STATUSES, list_sessions_for_user

router = APIRouter(prefix="/api", tags=["control-plane"])

_SESSION_HOST_RE = re.compile(r"^s-([a-z0-9]{8})\.medforge\..+$")


@router.get("/me", response_model=ApiEnvelope[MeResponse])
def get_me(
    request: Request,
    principal: AuthPrincipal = Depends(get_current_user),
) -> ApiEnvelope[MeResponse]:
    return envelope(request, MeResponse(user_id=principal.user_id, role=principal.role, email=principal.email))


@router.get("/sessions/current", response_model=ApiEnvelope[SessionCurrentResponse])
def get_current_session(
    request: Request,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ApiEnvelope[SessionCurrentResponse]:
    active_rows = list_sessions_for_user(session, user_id=principal.user_id, statuses=ACTIVE_SESSION_STATUSES)
    current = active_rows[0] if active_rows else None
    return envelope(
        request,
        SessionCurrentResponse(session=SessionRead.model_validate(current) if current is not None else None),
    )


@router.post("/sessions", response_model=ApiEnvelope[SessionCreateResponse], status_code=status.HTTP_201_CREATED)
def create_session(
    request: Request,
    payload: SessionCreateRequest,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _origin_guard: None = Depends(require_allowed_origin),
) -> ApiEnvelope[SessionCreateResponse]:
    result = create_session_for_principal(
        payload=payload,
        principal=principal,
        session=session,
        settings=settings,
    )
    return envelope(request, result)


@router.post(
    "/sessions/{id}/stop",
    response_model=ApiEnvelope[SessionActionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def stop_session(
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
    )
    return envelope(request, result)


@router.get("/auth/session-proxy", response_model=ApiEnvelope[SessionActionResponse])
def session_proxy(
    request: Request,
    host: Annotated[str | None, Header(alias="Host")] = None,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> JSONResponse:
    if host is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session host not found.")

    hostname = host.split(":", 1)[0].lower()
    match = _SESSION_HOST_RE.match(hostname)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session host not found.")

    slug = match.group(1)
    session_row = session.exec(select(SessionRecord).where(SessionRecord.slug == slug)).first()
    if session_row is None or session_row.status != SessionStatus.RUNNING:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    if principal.role != Role.ADMIN and session_row.user_id != principal.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session access denied.")

    body = envelope(request, SessionActionResponse(message="Session proxy authorized.")).model_dump(mode="json")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        headers={"X-Upstream": f"mf-session-{slug}:8080"},
        content=body,
    )
