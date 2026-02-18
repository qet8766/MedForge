from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from app.api_contract import ApiEnvelope, envelope
from app.config import Settings, get_settings
from app.database import get_session
from app.deps import require_allowed_origin
from app.models import AuthSession, User
from app.rate_limit import require_auth_rate_limit
from app.schemas import AuthCredentials, AuthUserResponse, SessionActionResponse
from app.security import create_session_token, hash_password, hash_session_token, normalize_email, verify_password
from app.util import commit_and_refresh, utcnow

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_samesite(settings: Settings) -> Literal["lax", "strict", "none"]:
    value = settings.cookie_samesite.lower()
    if value in {"lax", "strict", "none"}:
        return cast(Literal["lax", "strict", "none"], value)
    return "lax"


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    max_age = settings.auth_max_ttl_seconds
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=_cookie_samesite(settings),
        domain=settings.cookie_domain or None,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        domain=settings.cookie_domain or None,
        path="/",
    )


def _issue_auth_session(
    *,
    user_id: UUID,
    request: Request,
    session: Session,
    settings: Settings,
) -> str:
    token = create_session_token()
    now = utcnow()
    auth_session = AuthSession(
        user_id=user_id,
        token_hash=hash_session_token(token, settings.session_secret),
        created_at=now,
        expires_at=now + timedelta(seconds=settings.auth_idle_ttl_seconds),
        last_seen_at=now,
        ip=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent", "")[:512] or None,
    )
    session.add(auth_session)
    session.commit()
    return token


def _validate_email(email: str) -> str:
    normalized = normalize_email(email)
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid email address.")
    return normalized


@router.post("/signup", response_model=ApiEnvelope[AuthUserResponse], status_code=status.HTTP_201_CREATED)
def signup(
    payload: AuthCredentials,
    response: Response,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _origin_guard: None = Depends(require_allowed_origin),
    _rate_limit: None = Depends(require_auth_rate_limit),
) -> ApiEnvelope[AuthUserResponse]:
    email = _validate_email(payload.email)
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
    )
    commit_and_refresh(session, user)

    token = _issue_auth_session(user_id=user.id, request=request, session=session, settings=settings)
    _set_session_cookie(response, token, settings)

    return envelope(
        request,
        AuthUserResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            can_use_internal=user.can_use_internal,
        ),
    )


@router.post("/login", response_model=ApiEnvelope[AuthUserResponse])
def login(
    payload: AuthCredentials,
    response: Response,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _origin_guard: None = Depends(require_allowed_origin),
    _rate_limit: None = Depends(require_auth_rate_limit),
) -> ApiEnvelope[AuthUserResponse]:
    email = _validate_email(payload.email)
    user = session.exec(select(User).where(User.email == email)).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = _issue_auth_session(user_id=user.id, request=request, session=session, settings=settings)
    _set_session_cookie(response, token, settings)

    return envelope(
        request,
        AuthUserResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            can_use_internal=user.can_use_internal,
        ),
    )


@router.post("/logout", response_model=ApiEnvelope[SessionActionResponse])
def logout(
    response: Response,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _origin_guard: None = Depends(require_allowed_origin),
) -> ApiEnvelope[SessionActionResponse]:
    token = request.cookies.get(settings.cookie_name)
    if token:
        token_hash = hash_session_token(token, settings.session_secret)
        revoked_at_col = cast(Any, AuthSession.revoked_at)
        auth_session = session.exec(
            select(AuthSession).where(AuthSession.token_hash == token_hash).where(revoked_at_col.is_(None))
        ).first()
        if auth_session is not None:
            auth_session.revoked_at = utcnow()
            session.add(auth_session)
            session.commit()

    _clear_session_cookie(response, settings)
    return envelope(request, SessionActionResponse(message="Signed out."))
