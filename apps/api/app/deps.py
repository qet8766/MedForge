from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.database import get_session
from app.models import AuthSession, Role, User
from app.security import hash_session_token


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: UUID
    role: Role
    email: str | None
    auth_session_id: UUID | None
    source: str


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_allowed_origin(origin: str, settings: Settings) -> bool:
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"}:
        return False

    hostname = parsed.hostname
    if hostname is None:
        return False

    if hostname in {"localhost", "127.0.0.1"}:
        return True

    domain = settings.domain.strip().lower()
    if not domain:
        return False

    if hostname in {f"medforge.{domain}", f"api.medforge.{domain}"}:
        return True

    return hostname.endswith(f".medforge.{domain}")


def require_allowed_origin(
    origin: Annotated[str | None, Header(alias="Origin")] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if origin is None:
        return

    if not _is_allowed_origin(origin, settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin is not allowed.",
        )


def _principal_from_cookie(
    token: str,
    session: Session,
    settings: Settings,
) -> AuthPrincipal | None:
    token_hash = hash_session_token(token, settings.session_secret)
    statement = (
        select(AuthSession, User)
        .where(User.id == AuthSession.user_id)
        .where(AuthSession.token_hash == token_hash)
    )

    row = session.exec(statement).first()
    if row is None:
        return None

    auth_session, user = row

    now = _utcnow()
    created_at = _as_utc(auth_session.created_at)
    expires_at = _as_utc(auth_session.expires_at)
    hard_expires_at = created_at + timedelta(seconds=settings.auth_max_ttl_seconds)

    if auth_session.revoked_at is not None or expires_at <= now or hard_expires_at <= now:
        if auth_session.revoked_at is None:
            auth_session.revoked_at = now
            session.add(auth_session)
            session.commit()
        return None

    new_expires_at = min(now + timedelta(seconds=settings.auth_idle_ttl_seconds), hard_expires_at)
    auth_session.expires_at = new_expires_at
    auth_session.last_seen_at = now
    session.add(auth_session)
    session.commit()

    return AuthPrincipal(
        user_id=user.id,
        role=user.role,
        email=user.email,
        auth_session_id=auth_session.id,
        source="cookie",
    )


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthPrincipal:
    cookie_token = request.cookies.get(settings.cookie_name)
    if cookie_token:
        principal = _principal_from_cookie(cookie_token, session, settings)
        if principal is not None:
            return principal

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )


def get_current_user_id(principal: AuthPrincipal = Depends(get_current_user)) -> UUID:
    return principal.user_id


def require_admin_access(
    principal: AuthPrincipal = Depends(get_current_user),
) -> None:
    if principal.role == Role.ADMIN:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required.",
    )
