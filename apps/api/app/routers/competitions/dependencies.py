from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlmodel import Session

from app.config import Settings, get_settings
from app.database import get_session
from app.deps import AuthPrincipal, get_current_user, require_admin_access, require_allowed_origin
from app.models import Exposure

from .errors import from_http_exception


def require_allowed_origin_checked(
    origin: Annotated[str | None, Header(alias="Origin")] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    try:
        require_allowed_origin(origin=origin, settings=settings)
    except HTTPException as exc:
        raise from_http_exception(exc, type_slug="origin-not-allowed") from exc


def get_current_user_checked(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthPrincipal:
    try:
        return get_current_user(
            request=request,
            session=session,
            settings=settings,
        )
    except HTTPException as exc:
        raise from_http_exception(exc, type_slug="authentication-failed") from exc


def get_current_user_id_checked(principal: AuthPrincipal = Depends(get_current_user_checked)) -> UUID:
    return principal.user_id


def require_admin_access_checked(
    principal: AuthPrincipal = Depends(get_current_user_checked),
) -> None:
    try:
        require_admin_access(
            principal=principal,
        )
    except HTTPException as exc:
        raise from_http_exception(exc, type_slug="admin-access-denied") from exc


def bind_exposure(exposure: Exposure):
    def _bind(request: Request) -> None:
        request.state.competition_exposure = exposure

    return _bind


def get_bound_exposure(request: Request) -> Exposure:
    exposure = getattr(request.state, "competition_exposure", None)
    if isinstance(exposure, Exposure):
        return exposure
    raise HTTPException(status_code=500, detail="Competition exposure context missing.")
