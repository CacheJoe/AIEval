"""Evaluation orchestration service."""

from __future__ import annotations

from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import joinedload, Session

from app.evaluation.ai_content import detect_ai_generated_content
from app.evaluation.forensics import analyze_screenshots
from app.evaluation.pdf_processing import extract_document
from app.evaluation.plagiarism import compute_similarity_edges, summarize_plagiarism
from app.evaluation.relevance import relevance_score
from app.evaluation.scoring import score_submission
from app.models.academic import Experiment, Result, Submission
from app.models.enums import AuditAction, SimilarityLevel, SubmissionStatus
from app.models.user import User
from app.schemas.result import EvaluationRunResponse, ResultRead
from app.services.audit_service import AuditService
from app.storage.service import get_storage_provider
from app.utils.config import get_settings
from app.utils.exceptions import AppException
from app.utils.submission_labels import derive_submitter_label

settings = get_settings()


class EvaluationService:
    """Run experiment-level evaluation and reporting."""

    @staticmethod
    def _result_rows(db: Session, experiment_id: str) -> list[ResultRead]:
        stmt = (
            select(Submission)
            .where(Submission.experiment_id == experiment_id)
            .options(joinedload(Submission.student), joinedload(Submission.result))
            .order_by(Submission.uploaded_at.desc())
        )

        submissions = list(db.scalars(stmt).unique())
        results: list[ResultRead] = []
        for submission in submissions:
            if submission.result is None:
                continue
            plagiarism_matches = submission.result.breakdown.get("plagiarism_matches", []) if submission.result.breakdown else []
            results.append(
                ResultRead(
                    submission_id=submission.id,
                    submitter_label=submission.student.name if submission.student else derive_submitter_label(submission.filename),
                    filename=submission.filename,
                    marks=submission.result.marks,
                    score_out_of_5=submission.result.marks,
                    plagiarism_score=submission.result.plagiarism_score,
                    plagiarism_level=submission.result.plagiarism_level,
                    ai_generated_score=float((submission.result.flags or {}).get("ai_generated_score", 0.0)),
                    ai_generated_level=SimilarityLevel((submission.result.flags or {}).get("ai_generated_level", SimilarityLevel.LOW)),
                    top_classmate_similarity=round(
                        max((float(match.get("combined_score", 0.0)) for match in plagiarism_matches), default=0.0),
                        4,
                    ),
                    classmate_match_count=len(plagiarism_matches),
                    relevance_score=submission.result.relevance_score,
                    flags=submission.result.flags or {},
                    breakdown=submission.result.breakdown or {},
                    created_at=submission.result.created_at,
                )
            )
        return results

    @staticmethod
    def list_results(db: Session, experiment_id: str) -> list[ResultRead]:
        """List results for an experiment."""
        return EvaluationService._result_rows(db, experiment_id)

    @staticmethod
    def evaluate_experiment(db: Session, experiment: Experiment, actor: User) -> tuple[EvaluationRunResponse, dict]:
        """Run the full evaluation pipeline for an experiment."""
        if experiment.locked:
            raise AppException(status_code=409, message="Experiment results are locked.")

        submissions = list(
            db.scalars(
                select(Submission)
                .where(Submission.experiment_id == experiment.id)
                .options(joinedload(Submission.student), joinedload(Submission.result))
                .order_by(Submission.uploaded_at.asc())
            ).unique()
        )
        if not submissions:
            raise AppException(status_code=400, message="No submissions found for this experiment.")

        existing_results = {
            result.submission_id: result
            for result in db.scalars(
                select(Result).where(Result.submission_id.in_([submission.id for submission in submissions]))
            )
        }

        storage = get_storage_provider()
        extracted_documents = {}
        extraction_failures: dict[str, str] = {}
        for submission in submissions:
            try:
                extracted_documents[submission.id] = extract_document(
                    storage.resolve_path(submission.file_path),
                    include_images=settings.enable_screenshot_forensics,
                )
            except Exception as exc:
                extraction_failures[submission.id] = str(exc)

        document_texts = {submission_id: document.text for submission_id, document in extracted_documents.items()}

        similarity_edges = compute_similarity_edges(document_texts)
        plagiarism_summary = summarize_plagiarism(similarity_edges)
        screenshot_summary = {}
        if settings.enable_screenshot_forensics:
            image_lookup = {
                submission_id: [image.image for image in document.images]
                for submission_id, document in extracted_documents.items()
            }
            screenshot_summary = analyze_screenshots(image_lookup)

        for submission in submissions:
            existing_result = existing_results.get(submission.id) or submission.result
            if submission.id in extraction_failures:
                result = existing_result or Result(submission_id=submission.id)
                result.marks = 0.0
                result.plagiarism_score = 0.0
                result.plagiarism_level = SimilarityLevel.LOW
                result.relevance_score = 0.0
                result.flags = {"extraction_error": extraction_failures[submission.id]}
                result.breakdown = {"error": extraction_failures[submission.id]}
                if existing_result is None:
                    db.add(result)
                    submission.result = result
                submission.status = SubmissionStatus.REJECTED
                continue

            document = extracted_documents[submission.id]
            experiment_reference = "\n\n".join(
                value.strip()
                for value in [experiment.topic, experiment.description or ""]
                if value and value.strip()
            )
            relevance = relevance_score(experiment_reference, document.text)
            plagiarism = plagiarism_summary.get(submission.id, {"max_score": 0.0, "matches": []})
            ai_generated = detect_ai_generated_content(document.text)
            screenshots = screenshot_summary.get(
                submission.id,
                {
                    "has_screenshot": not settings.enable_screenshot_forensics,
                    "blank_screenshot_count": 0,
                    "duplicate_within_submission": False,
                    "duplicate_across_submissions": [],
                    "image_count": 0,
                },
            )
            score = score_submission(
                sections=document.sections,
                relevance=float(relevance["score"]),
                plagiarism_score=float(plagiarism["max_score"]),
                ai_generated_score=float(ai_generated["score"]),
                screenshot_analysis=screenshots,
            )

            flags = {
                "missing_sections": score["missing_sections"],
                "blank_screenshot_count": screenshots["blank_screenshot_count"],
                "duplicate_within_submission": screenshots["duplicate_within_submission"],
                "duplicate_across_submissions": screenshots["duplicate_across_submissions"],
                "semantic_method": relevance["method"],
                "screenshot_forensics_enabled": settings.enable_screenshot_forensics,
                "ai_generated_score": ai_generated["score"],
                "ai_generated_level": ai_generated["level"].value,
            }
            breakdown = {
                "headings": document.headings,
                "sections_detected": list(document.sections.keys()),
                "components": score["components"],
                "weights": score["weights"],
                "plagiarism_matches": plagiarism["matches"],
                "ai_generated_features": ai_generated["features"],
                "score_out_of_100": score["score_out_of_100"],
                "score_out_of_5": score["score_out_of_5"],
                "page_count": document.page_count,
                "image_count": screenshots["image_count"],
            }

            result = existing_result or Result(submission_id=submission.id)
            result.marks = score["marks"]
            result.plagiarism_score = round(float(plagiarism["max_score"]), 4)
            result.plagiarism_level = score["plagiarism_level"]
            result.relevance_score = round(float(relevance["score"]), 4)
            result.flags = flags
            result.breakdown = breakdown
            if existing_result is None:
                db.add(result)
                submission.result = result

            submission.status = SubmissionStatus.EVALUATED

        AuditService.record(
            db=db,
            action=AuditAction.EVALUATION_RUN,
            user_id=actor.id,
            entity_type="experiment",
            entity_id=experiment.id,
            details={"submission_count": len(submissions), "topic": experiment.topic},
        )
        db.commit()

        result_rows = EvaluationService._result_rows(db, experiment.id)
        response = EvaluationRunResponse(
            experiment_id=experiment.id,
            evaluated_count=len(result_rows),
            average_marks=round(mean([row.marks for row in result_rows]), 2) if result_rows else 0.0,
            graph_html_path=None,
            dashboard_html_path=None,
            results=result_rows,
        )
        return response, {}
