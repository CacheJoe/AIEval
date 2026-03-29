"""Class and experiment routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DBSession
from app.auth.dependencies import require_roles
from app.models.academic import Experiment, LabClass
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.schemas.academic import (
    ClassCreate,
    ClassDetail,
    ClassRead,
    ExperimentCreate,
    ExperimentRead,
)
from app.services.audit_service import AuditService
from app.services.class_service import ClassService
from app.utils.exceptions import AppException

router = APIRouter(tags=["Classes"])


def _class_read(lab_class: LabClass) -> ClassRead:
    return ClassRead(
        id=lab_class.id,
        name=lab_class.name,
        semester=lab_class.semester,
        faculty_id=lab_class.faculty_id,
        faculty_name=lab_class.faculty.name if lab_class.faculty else None,
        experiment_count=len(lab_class.experiments),
        submission_count=sum(len(experiment.submissions) for experiment in lab_class.experiments),
        created_at=lab_class.created_at,
        updated_at=lab_class.updated_at,
    )


def _experiment_read(experiment: Experiment) -> ExperimentRead:
    return ExperimentRead.model_validate(experiment)


@router.get("/classes", response_model=list[ClassRead], status_code=status.HTTP_200_OK)
def list_classes(db: DBSession, current_user: CurrentUser) -> list[ClassRead]:
    """List classes visible to the authenticated user."""
    classes = ClassService.list_classes(db, current_user)
    return [_class_read(lab_class) for lab_class in classes]


@router.post("/classes", response_model=ClassRead, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: ClassCreate,
    db: DBSession,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ClassRead:
    """Create a new class."""
    lab_class = ClassService.create_class(db, payload)
    AuditService.record(
        db=db,
        action=AuditAction.CLASS_CREATE,
        user_id=current_user.id,
        entity_type="class",
        entity_id=lab_class.id,
        details={"name": lab_class.name, "semester": lab_class.semester, "faculty_id": lab_class.faculty_id},
    )
    db.commit()
    db.refresh(lab_class)
    return _class_read(ClassService.get_class_for_user(db, lab_class.id, current_user))


@router.get("/classes/{class_id}", response_model=ClassDetail, status_code=status.HTTP_200_OK)
def get_class_detail(class_id: str, db: DBSession, current_user: CurrentUser) -> ClassDetail:
    """Get class details."""
    lab_class = ClassService.get_class_for_user(
        db=db,
        class_id=class_id,
        current_user=current_user,
    )
    return ClassDetail(
        **_class_read(lab_class).model_dump(),
        experiments=[_experiment_read(experiment) for experiment in lab_class.experiments],
    )


@router.get(
    "/classes/{class_id}/experiments",
    response_model=list[ExperimentRead],
    status_code=status.HTTP_200_OK,
)
def list_experiments(class_id: str, db: DBSession, current_user: CurrentUser) -> list[ExperimentRead]:
    """List experiments for a class."""
    lab_class = ClassService.get_class_for_user(
        db=db,
        class_id=class_id,
        current_user=current_user,
    )
    return [_experiment_read(experiment) for experiment in ClassService.list_experiments(db, lab_class)]


@router.post(
    "/classes/{class_id}/experiments",
    response_model=ExperimentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    class_id: str,
    payload: ExperimentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ExperimentRead:
    """Create an experiment for a class."""
    if current_user.role not in {UserRole.ADMIN, UserRole.FACULTY}:
        raise AppException(status_code=403, message="Only ADMIN or class FACULTY can create experiments.")

    lab_class = ClassService.get_class_for_user(db, class_id, current_user, write_access=True)
    experiment = ClassService.create_experiment(db, lab_class, payload)
    AuditService.record(
        db=db,
        action=AuditAction.EXPERIMENT_CREATE,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details={"class_id": class_id, "topic": experiment.topic},
    )
    db.commit()
    db.refresh(experiment)
    return _experiment_read(experiment)
