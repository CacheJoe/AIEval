"""Evaluation and results routes."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.models.enums import AuditAction, UserRole
from app.schemas.academic import ExperimentLockResponse
from app.schemas.result import EvaluationRunResponse, ResultRead
from app.services.audit_service import AuditService
from app.services.class_service import ClassService
from app.services.evaluation_service import EvaluationService
from app.utils.exceptions import AppException

router = APIRouter(tags=["Evaluation"])


@router.post(
    "/experiments/{experiment_id}/evaluate",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_200_OK,
)
def evaluate_experiment(experiment_id: str, db: DBSession, current_user: CurrentUser) -> EvaluationRunResponse:
    """Run evaluation for an experiment batch."""
    if current_user.role not in {UserRole.ADMIN, UserRole.FACULTY}:
        raise AppException(status_code=403, message="Only ADMIN or FACULTY can run evaluation.")

    experiment = ClassService.get_experiment_for_user(db, experiment_id, current_user, write_access=True)
    response, _ = EvaluationService.evaluate_experiment(db, experiment, current_user)
    return response


@router.get(
    "/experiments/{experiment_id}/results",
    response_model=list[ResultRead],
    status_code=status.HTTP_200_OK,
)
def list_experiment_results(experiment_id: str, db: DBSession, current_user: CurrentUser) -> list[ResultRead]:
    """List evaluated results for an experiment."""
    if current_user.role not in {UserRole.ADMIN, UserRole.FACULTY}:
        raise AppException(status_code=403, message="You do not have permission to view evaluation results.")

    experiment = ClassService.get_experiment_for_user(db, experiment_id, current_user)
    AuditService.record(
        db=db,
        action=AuditAction.RESULT_VIEW,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details={"scope": "experiment"},
    )
    db.commit()
    return EvaluationService.list_results(db, experiment.id)


@router.post(
    "/experiments/{experiment_id}/lock",
    response_model=ExperimentLockResponse,
    status_code=status.HTTP_200_OK,
)
def lock_experiment_results(experiment_id: str, db: DBSession, current_user: CurrentUser) -> ExperimentLockResponse:
    """Lock experiment results."""
    experiment = ClassService.get_experiment_for_user(db, experiment_id, current_user)
    locked = ClassService.lock_experiment(experiment, current_user)
    AuditService.record(
        db=db,
        action=AuditAction.EXPERIMENT_LOCK,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=locked.id,
        details={"locked": locked.locked},
    )
    db.commit()
    return ExperimentLockResponse(
        experiment_id=locked.id,
        locked=locked.locked,
        locked_at=locked.locked_at,
    )
