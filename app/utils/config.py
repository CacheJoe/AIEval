"""Application settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

# Always writable on Streamlit / containers
DEFAULT_SQLITE_PATH = Path("/tmp/aiales.db")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# -----------------------------------------------------
# Detect Streamlit Cloud runtime
# -----------------------------------------------------

IS_STREAMLIT = os.getenv("STREAMLIT_SERVER_PORT") is not None

if IS_STREAMLIT:
    DEFAULT_SQLITE_PATH = Path("/tmp/aiales.db")
else:
    DEFAULT_SQLITE_PATH = Path("/tmp/aiales.db")


class Settings(BaseSettings):
    """Configuration loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / "config" / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Academic Integrity & Automated Lab Evaluation System"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
    auto_create_tables: bool = True

    jwt_secret_key: str = "change-this-secret-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 10080

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8501",
            "http://127.0.0.1:8501",
        ]
    )

    logs_dir: Path = PROJECT_ROOT / "logs"
    submissions_dir: Path = PROJECT_ROOT / "submissions"
    reports_dir: Path = PROJECT_ROOT / "reports"
    log_level: str = "INFO"

    max_upload_mb: int = 25
    allowed_document_extensions: list[str] = Field(
        default_factory=lambda: [".pdf", ".zip"]
    )
    allowed_archive_extensions: list[str] = Field(
        default_factory=lambda: [".zip"]
    )

    plagiarism_threshold_low: float = 0.35
    plagiarism_threshold_medium: float = 0.60
    plagiarism_threshold_high: float = 0.80

    semantic_similarity_cutoff: float = 0.45
    section_heading_similarity_threshold: float = 0.78
    blank_image_variance_threshold: float = 12.0
    screenshot_duplicate_similarity_threshold: float = 0.96

    marks_completeness_weight: float = 25.0
    marks_execution_weight: float = 25.0
    marks_theory_weight: float = 15.0
    marks_relevance_weight: float = 15.0
    marks_screenshot_weight: float = 10.0
    marks_plagiarism_penalty_weight: float = 10.0
    marks_ai_penalty_weight: float = 5.0

    plagiarism_tfidf_weight: float = 0.45
    plagiarism_ngram_weight: float = 0.25
    plagiarism_semantic_weight: float = 0.30

    ai_generated_threshold_low: float = 0.35
    ai_generated_threshold_medium: float = 0.55
    ai_generated_threshold_high: float = 0.75

    semantic_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    relevance_engine: Literal[
        "tfidf",
        "sentence_transformer",
        "auto",
    ] = "tfidf"

    enable_screenshot_forensics: bool = False
    auto_generate_reports_on_evaluation: bool = False

    storage_backend: Literal["local"] = "local"

    frontend_api_base_url: str = "http://127.0.0.1:8000/api/v1"

    # -----------------------------------------------------

    def ensure_directories(self) -> None:
        """Create runtime directories if missing."""

        runtime_dirs = [
            self.logs_dir,
            self.submissions_dir,
            self.reports_dir,
            self.reports_dir / "graphs",
        ]

        # Only create database directory locally
        if not IS_STREAMLIT:
            runtime_dirs.append(PROJECT_ROOT / "database")

        for path in runtime_dirs:
            path.mkdir(parents=True, exist_ok=True)

        print("Using database:", self.database_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""
    settings = Settings()
    settings.ensure_directories()
    return settings
