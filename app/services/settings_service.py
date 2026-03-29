"""Runtime configuration read service."""

from __future__ import annotations

from app.schemas.settings import RuntimeSettingsRead
from app.utils.config import get_settings


class SettingsService:
    """Expose selected runtime settings."""

    @staticmethod
    def read_runtime_settings() -> RuntimeSettingsRead:
        """Return safe runtime settings for administrators."""
        settings = get_settings()
        return RuntimeSettingsRead(
            environment=settings.environment,
            database_url=settings.database_url,
            upload_limits={
                "max_upload_mb": settings.max_upload_mb,
                "allowed_document_extensions": settings.allowed_document_extensions,
                "allowed_archive_extensions": settings.allowed_archive_extensions,
            },
            thresholds={
                "plagiarism_low": settings.plagiarism_threshold_low,
                "plagiarism_medium": settings.plagiarism_threshold_medium,
                "plagiarism_high": settings.plagiarism_threshold_high,
                "semantic_similarity_cutoff": settings.semantic_similarity_cutoff,
                "section_heading_similarity_threshold": settings.section_heading_similarity_threshold,
                "blank_image_variance_threshold": settings.blank_image_variance_threshold,
                "screenshot_duplicate_similarity_threshold": settings.screenshot_duplicate_similarity_threshold,
            },
            scoring={
                "completeness": settings.marks_completeness_weight,
                "execution": settings.marks_execution_weight,
                "theory": settings.marks_theory_weight,
                "relevance": settings.marks_relevance_weight,
                "screenshot": settings.marks_screenshot_weight,
                "plagiarism_penalty": settings.marks_plagiarism_penalty_weight,
            },
            storage_backend=settings.storage_backend,
            semantic_model_name=settings.semantic_model_name,
        )

