from __future__ import annotations

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Response, status
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.database import get_session
from app.deps import AuthPrincipal, get_current_user
from app.models import Role, SessionRecord, SessionStatus
from app.schemas import MeResponse, SessionCreateRequest, SessionCreateResponse, SessionStopResponse
from app.session_lifecycle import create_session_for_principal, stop_session_for_principal

router = APIRouter(prefix="/api", tags=["control-plane"])

_SESSION_HOST_RE = re.compile(r"^s-([a-z0-9]{8})\.medforge\..+$")


@router.get("/me", response_model=MeResponse)
def get_me(principal: AuthPrincipal = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user_id=principal.user_id, role=principal.role, email=principal.email)


@router.post("/sessions", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionCreateResponse:
    return create_session_for_principal(
        payload=payload,
        principal=principal,
        session=session,
        settings=settings,
    )


@router.post(
    "/sessions/{id}/stop",
    response_model=SessionStopResponse,
)
def stop_session(
    session_id: UUID = Path(alias="id"),
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionStopResponse:
    return stop_session_for_principal(
        session_id=session_id,
        principal=principal,
        session=session,
        settings=settings,
    )


@router.get("/auth/session-proxy")
def session_proxy(
    host: Annotated[str | None, Header(alias="Host")] = None,
    principal: AuthPrincipal = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
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

    return Response(status_code=status.HTTP_200_OK, headers={"X-Upstream": f"mf-session-{slug}:8080"})
