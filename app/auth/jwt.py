"""JWT creation and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from jose import JWTError, jwt

from app.utils.config import get_settings
from app.utils.exceptions import AppException

settings = get_settings()


@dataclass(slots=True)
class TokenPayload:
    """Decoded JWT payload."""

    subject: str
    role: str
    token_type: str
    jti: str
    expires_at: datetime


@dataclass(slots=True)
class EncodedToken:
    """Encoded JWT plus metadata."""

    token: str
    jti: str
    expires_at: datetime


def _build_token(subject: str, role: str, token_type: str, expires_delta: timedelta) -> EncodedToken:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + expires_delta
    jti = str(uuid4())
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return EncodedToken(token=token, jti=jti, expires_at=expires_at)


def create_access_token(subject: str, role: str) -> EncodedToken:
    """Issue an access token."""
    return _build_token(
        subject=subject,
        role=role,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str, role: str) -> EncodedToken:
    """Issue a refresh token."""
    return _build_token(
        subject=subject,
        role=role,
        token_type="refresh",
        expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes),
    )


def decode_token(token: str, expected_type: str) -> TokenPayload:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AppException(status_code=401, message="Invalid or expired token.") from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise AppException(status_code=401, message="Token type is not valid for this operation.")

    subject = payload.get("sub")
    role = payload.get("role")
    jti = payload.get("jti")
    exp = payload.get("exp")

    if not all([subject, role, jti, exp]):
        raise AppException(status_code=401, message="Token payload is incomplete.")

    expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    return TokenPayload(
        subject=str(subject),
        role=str(role),
        token_type=str(token_type),
        jti=str(jti),
        expires_at=expires_at,
    )


def hash_token(token: str) -> str:
    """Hash a token before storing it in the database."""
    return sha256(token.encode("utf-8")).hexdigest()

