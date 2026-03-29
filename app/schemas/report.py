"""Reporting schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ReportArtifact(BaseModel):
    """Generated report artifact."""

    name: str
    relative_path: str
    absolute_path: str


class ExperimentReportSummary(BaseModel):
    """Experiment report bundle."""

    experiment_id: str
    average_marks: float
    submission_count: int
    plagiarism_high_count: int
    cluster_count: int
    top_sources: list[dict[str, Any]]
    artifacts: list[ReportArtifact]

