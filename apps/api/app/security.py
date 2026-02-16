from __future__ import annotations

import hashlib
import hmac
import secrets

from passlib.context import CryptContext

_PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return _PASSWORD_CONTEXT.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _PASSWORD_CONTEXT.verify(password, password_hash)


def create_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str, session_secret: str) -> str:
    return hmac.new(session_secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()
