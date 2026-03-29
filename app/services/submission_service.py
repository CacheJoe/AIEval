"""Submission upload and listing services."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4
import zipfile

from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.academic import Experiment, Submission
from app.models.enums import SubmissionStatus, UserRole
from app.schemas.submission import SubmissionBatchItem, SubmissionBatchResponse, SubmissionRead
from app.schemas.user import UserCreate
from app.services.user_service import UserService
from app.storage.service import get_storage_provider
from app.utils.config import get_settings
from app.utils.exceptions import AppException
from app.utils.submission_labels import derive_submitter_label

settings = get_settings()


class SubmissionService:
    """Submission ingestion and retrieval."""

    @staticmethod
    def _safe_filename(filename: str) -> str:
        stem = "".join(character if character.isalnum() or character in "._-" else "_" for character in filename.strip())
        return stem or f"submission_{uuid4().hex}.pdf"

    @staticmethod
    def _flatten_uploads(files: list[UploadFile]) -> list[tuple[str, bytes]]:
        extracted: list[tuple[str, bytes]] = []
        for upload in files:
            filename = upload.filename or f"upload_{uuid4().hex}"
            suffix = Path(filename).suffix.lower()
            content = upload.file.read()
            if not content:
                continue

            if suffix == ".pdf":
                extracted.append((filename, content))
                continue

            if suffix == ".zip":
                with zipfile.ZipFile(BytesIO(content)) as archive:
                    for member_name in archive.namelist():
                        if member_name.endswith("/") or Path(member_name).suffix.lower() != ".pdf":
                            continue
                        extracted.append((Path(member_name).name, archive.read(member_name)))
                continue

            raise AppException(status_code=400, message=f"Unsupported upload type: {suffix}")
        return extracted

    @staticmethod
    def _explicit_label(filename: str, manifest_map: dict[str, str] | None = None) -> str | None:
        if not manifest_map:
            return None
        return manifest_map.get(filename) or manifest_map.get(Path(filename).name)

    @staticmethod
    def _internal_submitter_identity(
        experiment: Experiment,
        filename: str,
        checksum: str,
        explicit_label: str | None,
    ) -> tuple[str, str]:
        """Generate a hidden internal user identity for persistence."""
        label = derive_submitter_label(filename, explicit_label)
        safe_local = "".join(character if character.isalnum() else "." for character in label.lower()).strip(".")
        safe_local = ".".join(segment for segment in safe_local.split(".") if segment) or "submission"
        suffix = sha256(f"{experiment.id}:{filename}:{checksum}".encode("utf-8")).hexdigest()[:12]
        email = f"{safe_local[:40]}.{suffix}@aialesapp.com"
        return label, email

    @staticmethod
    def _resolve_internal_submitter(
        db: Session,
        experiment: Experiment,
        filename: str,
        checksum: str,
        explicit_label: str | None,
    ) -> tuple[str, str]:
        """Create or reuse the hidden internal submitter record for this file."""
        submitter_label, internal_email = SubmissionService._internal_submitter_identity(
            experiment=experiment,
            filename=filename,
            checksum=checksum,
            explicit_label=explicit_label,
        )
        user = UserService.get_user_by_email(db, internal_email)
        if user is None:
            try:
                user = UserService.create_user(
                    db,
                    UserCreate(
                        email=internal_email,
                        name=submitter_label,
                        role=UserRole.STUDENT,
                        password=f"AutoUpload!{uuid4().hex[:10]}",
                        is_active=True,
                    ),
                )
            except ValidationError as exc:
                raise AppException(
                    status_code=400,
                    message="Could not generate an internal submitter record for this file.",
                    details={"filename": filename, "errors": exc.errors()},
                ) from exc
        return submitter_label, user.id

    @staticmethod
    def upload_batch(
        db: Session,
        experiment: Experiment,
        files: list[UploadFile],
        manifest_map: dict[str, str] | None = None,
    ) -> SubmissionBatchResponse:
        """Save uploaded PDF submissions for an experiment."""
        if experiment.locked:
            raise AppException(status_code=409, message="Experiment is locked and cannot accept new submissions.")

        upload_entries = SubmissionService._flatten_uploads(files)
        if not upload_entries:
            raise AppException(status_code=400, message="No PDF files were provided.")

        storage = get_storage_provider()
        items: list[SubmissionBatchItem] = []
        created_count = 0
        updated_count = 0
        failed_count = 0

        for original_filename, content in upload_entries:
            if len(content) > settings.max_upload_mb * 1024 * 1024:
                items.append(
                    SubmissionBatchItem(
                        filename=original_filename,
                        message=f"File exceeds the {settings.max_upload_mb} MB limit.",
                    )
                )
                failed_count += 1
                continue

            checksum = sha256(content).hexdigest()
            explicit_label = SubmissionService._explicit_label(original_filename, manifest_map)
            submitter_label, internal_submitter_id = SubmissionService._resolve_internal_submitter(
                db=db,
                experiment=experiment,
                filename=original_filename,
                checksum=checksum,
                explicit_label=explicit_label,
            )

            relative_path = (
                f"submissions/class_{experiment.class_id}/experiment_{experiment.id}/"
                f"file_{uuid4().hex}_{SubmissionService._safe_filename(original_filename)}"
            )
            artifact = storage.save_bytes(relative_path, content)

            submission = db.scalar(
                select(Submission)
                .where(
                    Submission.experiment_id == experiment.id,
                    Submission.student_id == internal_submitter_id,
                    Submission.filename == original_filename,
                    Submission.checksum == checksum,
                )
                .options(joinedload(Submission.result))
            )

            created = submission is None
            updated = False
            if submission is None:
                submission = Submission(
                    experiment_id=experiment.id,
                    student_id=internal_submitter_id,
                    filename=original_filename,
                    file_path=artifact.relative_path,
                    file_size_bytes=artifact.size_bytes,
                    checksum=checksum,
                    status=SubmissionStatus.UPLOADED,
                )
                db.add(submission)
                db.flush()
                created_count += 1
            else:
                submission.file_path = artifact.relative_path
                submission.file_size_bytes = artifact.size_bytes
                submission.status = SubmissionStatus.UPLOADED
                submission.uploaded_at = datetime.now(timezone.utc)
                if submission.result is not None:
                    db.delete(submission.result)
                db.flush()
                updated = True
                updated_count += 1

            items.append(
                SubmissionBatchItem(
                    filename=original_filename,
                    submitter_label=submitter_label,
                    submission_id=submission.id,
                    created=created,
                    updated=updated,
                    message="Uploaded successfully.",
                )
            )

        response = SubmissionBatchResponse(
            created_count=created_count,
            updated_count=updated_count,
            failed_count=failed_count,
            items=items,
        )
        if created_count == 0 and updated_count == 0:
            raise AppException(
                status_code=400,
                message="No submissions were saved for this experiment.",
                details=response.model_dump(),
            )
        return response

    @staticmethod
    def list_submissions(db: Session, experiment_id: str) -> list[SubmissionRead]:
        """List submissions for an experiment."""
        rows = db.execute(
            select(Submission)
            .where(Submission.experiment_id == experiment_id)
            .options(joinedload(Submission.student), joinedload(Submission.result))
            .order_by(Submission.uploaded_at.desc())
        ).scalars()

        return [
            SubmissionRead(
                id=submission.id,
                experiment_id=submission.experiment_id,
                submitter_label=(
                    submission.student.name if submission.student else derive_submitter_label(submission.filename)
                ),
                filename=submission.filename,
                file_path=submission.file_path,
                status=submission.status,
                uploaded_at=submission.uploaded_at,
                marks=submission.result.marks if submission.result else None,
            )
            for submission in rows
        ]
