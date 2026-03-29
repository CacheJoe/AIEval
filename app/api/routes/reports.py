"""Report routes."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DBSession
from app.models.enums import AuditAction, UserRole
from app.schemas.report import ExperimentReportSummary
from app.schemas.result import PlagiarismNetworkResponse
from app.services.audit_service import AuditService
from app.services.class_service import ClassService
from app.services.evaluation_service import EvaluationService
from app.services.report_service import ReportService
from app.utils.exceptions import AppException

router = APIRouter(tags=["Reports"])


def _build_bundle(db, experiment):
    rows = EvaluationService.list_results(db, experiment.id)
    if not rows:
        raise AppException(status_code=400, message="Run evaluation before generating reports.")

    submission_lookup = {row.submission_id: {"label": row.submitter_label, "filename": row.filename} for row in rows}
    edges = ReportService.reconstruct_edges(rows)
    return ReportService.generate_report_bundle(experiment, rows, submission_lookup, edges)


def _authorize_report_access(db, experiment_id, current_user):
    if current_user.role not in {UserRole.ADMIN, UserRole.FACULTY}:
        raise AppException(status_code=403, message="You do not have permission to access reports.")
    return ClassService.get_experiment_for_user(db, experiment_id, current_user)


@router.get(
    "/experiments/{experiment_id}/reports",
    response_model=ExperimentReportSummary,
    status_code=status.HTTP_200_OK,
)
def get_report_summary(experiment_id: str, db: DBSession, current_user: CurrentUser) -> ExperimentReportSummary:
    """Generate and return report metadata for an experiment."""
    experiment = _authorize_report_access(db, experiment_id, current_user)
    summary, _ = _build_bundle(db, experiment)
    AuditService.record(
        db=db,
        action=AuditAction.REPORT_EXPORT,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details={"artifact": "bundle"},
    )
    db.commit()
    return summary


@router.get(
    "/experiments/{experiment_id}/reports/network/data",
    response_model=PlagiarismNetworkResponse,
    status_code=status.HTTP_200_OK,
)
def get_network_data(experiment_id: str, db: DBSession, current_user: CurrentUser) -> PlagiarismNetworkResponse:
    """Return plagiarism network graph metadata."""
    experiment = _authorize_report_access(db, experiment_id, current_user)
    _, network = _build_bundle(db, experiment)
    AuditService.record(
        db=db,
        action=AuditAction.REPORT_EXPORT,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details={"artifact": "network_data"},
    )
    db.commit()
    return network


@router.get("/experiments/{experiment_id}/reports/csv", status_code=status.HTTP_200_OK)
def download_marks_csv(experiment_id: str, db: DBSession, current_user: CurrentUser) -> FileResponse:
    """Download marks CSV."""
    experiment = _authorize_report_access(db, experiment_id, current_user)
    summary, _ = _build_bundle(db, experiment)
    artifact = next(item for item in summary.artifacts if item.name == "marks_csv")
    AuditService.record(
        db=db,
        action=AuditAction.REPORT_EXPORT,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details={"artifact": "marks_csv"},
    )
    db.commit()
    return FileResponse(path=artifact.absolute_path, filename=f"{experiment.topic}_marks.csv")


@router.get("/experiments/{experiment_id}/reports/pdf", status_code=status.HTTP_200_OK)
def download_summary_pdf(experiment_id: str, db: DBSession, current_user: CurrentUser) -> FileResponse:
    """Download summary PDF."""
    experiment = _authorize_report_access(db, experiment_id, current_user)
    summary, _ = _build_bundle(db, experiment)
    artifact = next(item for item in summary.artifacts if item.name == "summary_pdf")
    AuditService.record(
        db=db,
        action=AuditAction.REPORT_EXPORT,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details={"artifact": "summary_pdf"},
    )
    db.commit()
    return FileResponse(path=artifact.absolute_path, filename=f"{experiment.topic}_summary.pdf")


@router.get("/experiments/{experiment_id}/reports/dashboard", status_code=status.HTTP_200_OK)
def download_dashboard_html(experiment_id: str, db: DBSession, current_user: CurrentUser) -> FileResponse:
    """Download dashboard HTML."""
    experiment = _authorize_report_access(db, experiment_id, current_user)
    summary, _ = _build_bundle(db, experiment)
    artifact = next((item for item in summary.artifacts if item.name == "dashboard_html"), None)
    if artifact is None:
        raise AppException(status_code=404, message="Dashboard artifact is not available.")
    AuditService.record(
        db=db,
        action=AuditAction.REPORT_EXPORT,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details={"artifact": "dashboard_html"},
    )
    db.commit()
    return FileResponse(path=artifact.absolute_path, filename=f"{experiment.topic}_dashboard.html")


@router.get("/experiments/{experiment_id}/reports/network", status_code=status.HTTP_200_OK)
def download_network_html(experiment_id: str, db: DBSession, current_user: CurrentUser) -> FileResponse:
    """Download the plagiarism network HTML."""
    experiment = _authorize_report_access(db, experiment_id, current_user)
    summary, network = _build_bundle(db, experiment)
    artifact = next((item for item in summary.artifacts if item.name == "plagiarism_network_html"), None)
    if artifact is None or network.html_relative_path is None:
        raise AppException(status_code=404, message="Network HTML artifact is not available.")
    AuditService.record(
        db=db,
        action=AuditAction.REPORT_EXPORT,
        user_id=current_user.id,
        entity_type="experiment",
        entity_id=experiment.id,
        details={"artifact": "plagiarism_network_html"},
    )
    db.commit()
    return FileResponse(path=artifact.absolute_path, filename=f"{experiment.topic}_network.html")
