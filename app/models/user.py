"""User model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.academic import ClassEnrollment, Experiment, LabClass, Submission
    from app.models.audit import AuditLog, RefreshToken


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """System user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=20), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")
    taught_classes: Mapped[list["LabClass"]] = relationship(
        "LabClass",
        back_populates="faculty",
        foreign_keys="LabClass.faculty_id",
    )
    class_memberships: Mapped[list["ClassEnrollment"]] = relationship("ClassEnrollment", back_populates="student")
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="student",
        foreign_keys="Submission.student_id",
    )
    locked_experiments: Mapped[list["Experiment"]] = relationship(
        "Experiment",
        back_populates="locked_by",
        foreign_keys="Experiment.locked_by_id",
    )

