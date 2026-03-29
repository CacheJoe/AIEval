"""Evaluation and result schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import SimilarityLevel


class ResultRead(BaseModel):
    """Submission result."""

    submission_id: str
    submitter_label: str
    filename: str
    marks: float
    score_out_of_5: float
    plagiarism_score: float
    plagiarism_level: SimilarityLevel
    ai_generated_score: float
    ai_generated_level: SimilarityLevel
    top_classmate_similarity: float
    classmate_match_count: int
    relevance_score: float
    flags: dict[str, Any]
    breakdown: dict[str, Any]
    created_at: datetime


class EvaluationRunResponse(BaseModel):
    """Evaluation batch response."""

    experiment_id: str
    evaluated_count: int
    average_marks: float
    graph_html_path: str | None = None
    dashboard_html_path: str | None = None
    results: list[ResultRead]


class PlagiarismNetworkResponse(BaseModel):
    """Network graph response."""

    experiment_id: str
    html_relative_path: str | None
    node_count: int
    edge_count: int
    cluster_count: int
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    top_sources: list[dict[str, Any]]
