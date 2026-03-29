"""User management service layer."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.exceptions import AppException

INTERNAL_SUBMITTER_DOMAIN = "@aialesapp.com"


class UserService:
    """User lookup and mutation helpers."""

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        """Find a user by normalized email."""
        normalized_email = email.strip().lower()
        return db.scalar(select(User).where(User.email == normalized_email))

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User | None:
        """Find a user by identifier."""
        return db.scalar(select(User).where(User.id == user_id))

    @staticmethod
    def list_users(db: Session) -> list[User]:
        """Return users ordered by creation date descending."""
        return list(
            db.scalars(
                select(User)
                .where(User.role.in_([UserRole.ADMIN, UserRole.FACULTY]))
                .order_by(User.created_at.desc())
            )
        )

    @staticmethod
    def create_user(db: Session, payload: UserCreate) -> User:
        """Create a new user account."""
        normalized_email = payload.email.strip().lower()
        if payload.role == UserRole.HOD:
            raise AppException(
                status_code=400,
                message="HOD accounts are disabled in the simplified admin and faculty workflow.",
            )
        if payload.role == UserRole.STUDENT and not normalized_email.endswith(INTERNAL_SUBMITTER_DOMAIN):
            raise AppException(
                status_code=400,
                message="Student account creation is disabled in the faculty-upload workflow.",
            )
        if UserService.get_user_by_email(db, normalized_email) is not None:
            raise AppException(status_code=409, message="A user with this email already exists.")

        user = User(
            email=normalized_email,
            name=payload.name.strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=payload.is_active,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def update_status(db: Session, user_id: str, is_active: bool) -> User:
        """Activate or deactivate an account."""
        user = UserService.get_user_by_id(db, user_id)
        if user is None:
            raise AppException(status_code=404, message="User was not found.")

        user.is_active = is_active
        db.flush()
        return user
