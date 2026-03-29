"""Submission routes."""

from __future__ import annotations

import json
from json import JSONDecodeError

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import CurrentUser, DBSession
from app.models.enums import AuditAction, UserRole
from app.schemas.submission import SubmissionBatchResponse, SubmissionRead
from app.services.audit_service import AuditService
from app.services.class_service import ClassService
from app.services.submission_service import SubmissionService
from app.utils.exceptions import AppException

router = APIRouter(tags=["Submissions"])


@router.get(
    "/experiments/{experiment_id}/submissions",
    response_model=list[SubmissionRead],
    status_code=status.HTTP_200_OK,
)
def list_submissions(experiment_id: str, db: DBSession, current_user: CurrentUser) -> list[SubmissionRead]:
    """List submissions for an experiment."""
    if current_user.role not in {UserRole.ADMIN, UserRole.FACULTY}:
        raise AppException(status_code=403, message="You do not have permission to view submissions.")

    experiment = ClassService.get_experiment_for_user(db, experiment_id, current_user)
    return SubmissionService.list_submissions(db, experiment.id)


@router.post(
    "/experiments/{experiment_id}/submissions/upload",
    response_model=SubmissionBatchResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_submissions(
    experiment_id: str,
    db: DBSession,
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
    manifest_json: str | None = Form(default=None),
) -> SubmissionBatchResponse:
    """Upload PDF or ZIP submission batches for an experiment."""
    if current_user.role not in {UserRole.ADMIN, UserRole.FACULTY}:
        raise AppException(status_code=403, message="Only ADMIN or FACULTY can upload submissions.")

    experiment = ClassService.get_experiment_for_user(db, experiment_id, current_user, write_access=True)
    manifest_map: dict[str, str] | None = None
    if manifest_json:
        try:
            parsed = json.loads(manifest_json)
        except JSONDecodeError as exc:
            raise AppException(status_code=400, message="manifest_json is not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise AppException(status_code=400, message="manifest_json must be an object mapping filename to label.")
        manifest_map = {str(key): str(value) for key, value in parsed.items()}

    response = SubmissionService.upload_batch(
        db=db,
        experiment=experiment,
        files=files,
        manifest_map=manifest_map,
    )
    AuditService.record(
        db=db,
        action=AuditAction.SUBMISSION_UPLOAD,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details=response.model_dump(),
    )
    db.commit()
    return response
