"""Class and experiment management services."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload, Session

from app.models.academic import Experiment, LabClass
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.academic import ClassCreate, ExperimentCreate
from app.services.user_service import UserService
from app.utils.exceptions import AppException


class ClassService:
    """Academic class and experiment helpers."""

    @staticmethod
    def list_classes(db: Session, current_user: User) -> list[LabClass]:
        """List classes visible to the current user."""
        stmt = (
            select(LabClass)
            .options(
                joinedload(LabClass.faculty),
                selectinload(LabClass.experiments).selectinload(Experiment.submissions),
            )
            .order_by(LabClass.created_at.desc())
        )

        if current_user.role == UserRole.FACULTY:
            stmt = stmt.where(LabClass.faculty_id == current_user.id)

        return list(db.scalars(stmt).unique())

    @staticmethod
    def create_class(db: Session, payload: ClassCreate) -> LabClass:
        """Create a new class and assign faculty."""
        faculty = UserService.get_user_by_id(db, payload.faculty_id)
        if faculty is None or faculty.role != UserRole.FACULTY:
            raise AppException(status_code=400, message="Assigned faculty user is invalid.")

        lab_class = LabClass(
            name=payload.name.strip(),
            semester=payload.semester.strip(),
            faculty_id=payload.faculty_id,
        )
        db.add(lab_class)
        db.flush()
        db.refresh(lab_class)
        return lab_class

    @staticmethod
    def get_class_for_user(
        db: Session,
        class_id: str,
        current_user: User,
        write_access: bool = False,
    ) -> LabClass:
        """Resolve a class with role-based access checks."""
        lab_class = db.scalar(
            select(LabClass)
            .where(LabClass.id == class_id)
            .options(
                joinedload(LabClass.faculty),
                selectinload(LabClass.experiments).selectinload(Experiment.submissions),
            )
        )
        if lab_class is None:
            raise AppException(status_code=404, message="Class was not found.")

        if current_user.role == UserRole.ADMIN:
            return lab_class
        if current_user.role == UserRole.FACULTY and lab_class.faculty_id == current_user.id:
            return lab_class

        action = "modify" if write_access else "view"
        raise AppException(status_code=403, message=f"You do not have permission to {action} this class.")

    @staticmethod
    def list_experiments(db: Session, lab_class: LabClass) -> list[Experiment]:
        """List experiments for a class."""
        return list(
            db.scalars(
                select(Experiment).where(Experiment.class_id == lab_class.id).order_by(Experiment.created_at.desc())
            )
        )

    @staticmethod
    def create_experiment(db: Session, lab_class: LabClass, payload: ExperimentCreate) -> Experiment:
        """Create a new experiment in a class."""
        description_parts = [payload.description.strip()] if payload.description else []
        if payload.context:
            description_parts.append(f"Context:\n{payload.context.strip()}")
        if payload.reference_content:
            description_parts.append(f"Reference Content:\n{payload.reference_content.strip()}")

        experiment = Experiment(
            class_id=lab_class.id,
            topic=payload.topic.strip(),
            description="\n\n".join(part for part in description_parts if part).strip() or None,
        )
        db.add(experiment)
        db.flush()
        db.refresh(experiment)
        return experiment

    @staticmethod
    def get_experiment_for_user(
        db: Session,
        experiment_id: str,
        current_user: User,
        write_access: bool = False,
    ) -> Experiment:
        """Resolve an experiment with class-based access control."""
        experiment = db.scalar(
            select(Experiment)
            .where(Experiment.id == experiment_id)
            .options(
                joinedload(Experiment.lab_class),
                joinedload(Experiment.locked_by),
            )
        )
        if experiment is None:
            raise AppException(status_code=404, message="Experiment was not found.")

        ClassService.get_class_for_user(
            db=db,
            class_id=experiment.class_id,
            current_user=current_user,
            write_access=write_access,
        )
        return experiment

    @staticmethod
    def lock_experiment(experiment: Experiment, current_user: User) -> Experiment:
        """Lock an experiment to make results read-only."""
        if current_user.role != UserRole.ADMIN:
            raise AppException(status_code=403, message="Only ADMIN can lock experiment results.")
        if experiment.locked:
            return experiment

        experiment.locked = True
        experiment.locked_at = datetime.now(timezone.utc)
        experiment.locked_by_id = current_user.id
        return experiment
