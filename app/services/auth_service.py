"""Authentication service layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token, create_refresh_token, decode_token, hash_token
from app.auth.password import verify_password
from app.models.audit import RefreshToken
from app.models.enums import AuditAction
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.user_service import UserService
from app.utils.exceptions import AppException


@dataclass(slots=True)
class IssuedTokenPair:
    """Issued access and refresh credentials."""

    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class AuthService:
    """Authentication and session management."""

    @staticmethod
    def _persist_token_pair(
        db: Session,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> IssuedTokenPair:
        """Create and store refresh token state without committing."""
        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

        db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh_token.token),
                expires_at=refresh_token.expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )
        db.flush()

        return IssuedTokenPair(
            access_token=access_token.token,
            refresh_token=refresh_token.token,
            access_token_expires_at=access_token.expires_at,
            refresh_token_expires_at=refresh_token.expires_at,
        )

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        """Validate user credentials."""
        user = UserService.get_user_by_email(db, email)
        if user is None or not verify_password(password, user.password_hash):
            raise AppException(status_code=401, message="Invalid email or password.")
        if not user.is_active:
            raise AppException(status_code=403, message="Your account is inactive.")
        return user

    @staticmethod
    def issue_token_pair(
        db: Session,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> IssuedTokenPair:
        """Create and persist a new access/refresh token pair."""
        token_pair = AuthService._persist_token_pair(
            db=db,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        AuditService.record(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user.id,
            details={"ip_address": ip_address, "user_agent": user_agent},
        )
        db.commit()
        return token_pair

    @staticmethod
    def rotate_refresh_token(
        db: Session,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, IssuedTokenPair]:
        """Rotate a refresh token and invalidate the previous one."""
        payload = decode_token(refresh_token, expected_type="refresh")
        stored_token = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(refresh_token),
                RefreshToken.revoked_at.is_(None),
            )
        )
        if stored_token is None or stored_token.expires_at <= datetime.now(timezone.utc):
            raise AppException(status_code=401, message="Refresh token is invalid or expired.")

        user = UserService.get_user_by_id(db, payload.subject)
        if user is None or not user.is_active:
            raise AppException(status_code=401, message="Associated user account is not available.")

        stored_token.revoked_at = datetime.now(timezone.utc)
        new_pair = AuthService._persist_token_pair(
            db=db,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        AuditService.record(
            db=db,
            action=AuditAction.TOKEN_REFRESH,
            user_id=user.id,
            details={"previous_token_id": stored_token.id},
        )
        db.commit()
        return user, new_pair

    @staticmethod
    def logout(
        db: Session,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Revoke a refresh token."""
        stored_token = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(refresh_token),
                RefreshToken.revoked_at.is_(None),
            )
        )
        if stored_token is None:
            raise AppException(status_code=401, message="Refresh token is invalid or already revoked.")

        stored_token.revoked_at = datetime.now(timezone.utc)
        AuditService.record(
            db=db,
            action=AuditAction.LOGOUT,
            user_id=stored_token.user_id,
            details={"ip_address": ip_address, "user_agent": user_agent},
        )
        db.commit()
