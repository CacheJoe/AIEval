"""Academic domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SimilarityLevel, SubmissionStatus

if TYPE_CHECKING:
    from app.models.user import User


class LabClass(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Course/lab class owned by faculty."""

    __tablename__ = "classes"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    semester: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    faculty_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    faculty: Mapped["User"] = relationship("User", back_populates="taught_classes", foreign_keys=[faculty_id])
    experiments: Mapped[list["Experiment"]] = relationship(
        "Experiment",
        back_populates="lab_class",
        cascade="all, delete-orphan",
    )
    enrollments: Mapped[list["ClassEnrollment"]] = relationship(
        "ClassEnrollment",
        back_populates="lab_class",
        cascade="all, delete-orphan",
    )


class ClassEnrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Student-to-class assignment."""

    __tablename__ = "class_enrollments"
    __table_args__ = (UniqueConstraint("class_id", "student_id", name="uq_class_enrollment"),)

    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    lab_class: Mapped["LabClass"] = relationship("LabClass", back_populates="enrollments")
    student: Mapped["User"] = relationship("User", back_populates="class_memberships")


class Experiment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Experiment configured within a class."""

    __tablename__ = "experiments"

    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    lab_class: Mapped["LabClass"] = relationship("LabClass", back_populates="experiments")
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="experiment",
        cascade="all, delete-orphan",
    )
    locked_by: Mapped["User | None"] = relationship(
        "User",
        back_populates="locked_experiments",
        foreign_keys=[locked_by_id],
    )


class Submission(UUIDPrimaryKeyMixin, Base):
    """Student file submission."""

    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("experiment_id", "student_id", name="uq_submission_experiment_student"),
    )

    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, native_enum=False, length=20),
        default=SubmissionStatus.UPLOADED,
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="submissions")
    student: Mapped["User"] = relationship("User", back_populates="submissions")
    result: Mapped["Result | None"] = relationship(
        "Result",
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Result(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Evaluation result per submission."""

    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_result_submission"),
        CheckConstraint("marks >= 0 AND marks <= 100", name="ck_results_marks_range"),
    )

    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    marks: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    plagiarism_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    plagiarism_level: Mapped[SimilarityLevel] = mapped_column(
        Enum(SimilarityLevel, native_enum=False, length=10),
        default=SimilarityLevel.LOW,
        nullable=False,
    )
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    flags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    submission: Mapped["Submission"] = relationship("Submission", back_populates="result")
