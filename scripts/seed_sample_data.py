"""Seed local development data for AIALES."""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.models.academic import Experiment, LabClass
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user_service import UserService


def ensure_user(db, email: str, name: str, role: UserRole, password: str) -> User:
    """Create a user if it does not already exist."""
    user = UserService.get_user_by_email(db, email)
    if user is not None:
        return user

    return UserService.create_user(
        db,
        UserCreate(email=email, name=name, role=role, password=password, is_active=True),
    )


def main() -> None:
    """Seed a baseline tenant-like dataset."""
    init_db()
    with SessionLocal() as db:
        admin = ensure_user(db, "admin@aiales.local", "System Admin", UserRole.ADMIN, "ChangeMe123!")
        faculty = ensure_user(db, "faculty@aiales.local", "Dr. Meera Sharma", UserRole.FACULTY, "Faculty123!")
        lab_class = db.scalar(select(LabClass).where(LabClass.name == "Data Science Lab", LabClass.semester == "Semester 6"))
        if lab_class is None:
            lab_class = LabClass(name="Data Science Lab", semester="Semester 6", faculty_id=faculty.id)
            db.add(lab_class)
            db.flush()

        experiment = db.scalar(
            select(Experiment).where(
                Experiment.class_id == lab_class.id,
                Experiment.topic == "K-Means Clustering",
            )
        )
        if experiment is None:
            db.add(
                Experiment(
                    class_id=lab_class.id,
                    topic="K-Means Clustering",
                    description="Segment the Iris dataset and analyze cluster purity.",
                )
            )

        db.commit()
        print("Seed complete.")
        print("Admin:", admin.email, "ChangeMe123!")
        print("Faculty:", faculty.email, "Faculty123!")


if __name__ == "__main__":
    main()
