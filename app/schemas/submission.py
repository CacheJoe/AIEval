"""Submission schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SubmissionStatus


class SubmissionRead(BaseModel):
    """Submission details."""

    id: str
    experiment_id: str
    submitter_label: str
    filename: str
    file_path: str
    status: SubmissionStatus
    uploaded_at: datetime
    marks: float | None = None


class SubmissionBatchItem(BaseModel):
    """One uploaded file result."""

    filename: str
    submitter_label: str | None = None
    submission_id: str | None = None
    created: bool = False
    updated: bool = False
    message: str


class SubmissionBatchResponse(BaseModel):
    """Batch upload result."""

    created_count: int
    updated_count: int
    failed_count: int
    items: list[SubmissionBatchItem]
