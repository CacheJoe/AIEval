"""Submission scoring engine."""

from __future__ import annotations

from typing import Any

from app.evaluation.section_detector import REQUIRED_SECTIONS
from app.models.enums import SimilarityLevel
from app.utils.config import get_settings

settings = get_settings()

SECTION_MIN_WORDS = {
    "experiment_title": 1,
    "aim": 3,
    "theory": 5,
    "algorithm": 5,
    "dataset": 3,
    "implementation": 5,
    "output": 3,
    "analysis": 5,
    "conclusion": 3,
}


def _word_count(text: str) -> int:
    return len((text or "").split())


def _bounded_ratio(value: float, ceiling: float) -> float:
    if ceiling <= 0:
        return 0.0
    return max(0.0, min(1.0, value / ceiling))


def _plagiarism_level(score: float) -> SimilarityLevel:
    if score >= settings.plagiarism_threshold_high:
        return SimilarityLevel.HIGH
    if score >= settings.plagiarism_threshold_medium:
        return SimilarityLevel.MEDIUM
    return SimilarityLevel.LOW


def score_submission(
    sections: dict[str, str],
    relevance: float,
    plagiarism_score: float,
    ai_generated_score: float,
    screenshot_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Compute a transparent score breakdown for a submission."""
    present_sections = [
        section
        for section in REQUIRED_SECTIONS
        if _word_count(sections.get(section, "")) >= SECTION_MIN_WORDS.get(section, 5)
    ]
    completeness_ratio = len(present_sections) / len(REQUIRED_SECTIONS)

    theory_ratio = sum(
        [
            _bounded_ratio(_word_count(sections.get("aim", "")), 40),
            _bounded_ratio(_word_count(sections.get("theory", "")), 180),
            _bounded_ratio(_word_count(sections.get("analysis", "")), 100),
            _bounded_ratio(_word_count(sections.get("conclusion", "")), 60),
        ]
    ) / 4
    execution_ratio = sum(
        [
            _bounded_ratio(_word_count(sections.get("algorithm", "")), 80),
            _bounded_ratio(_word_count(sections.get("dataset", "")), 60),
            _bounded_ratio(_word_count(sections.get("implementation", "")), 180),
            _bounded_ratio(_word_count(sections.get("output", "")), 120),
        ]
    ) / 4

    screenshot_ratio = 1.0
    if not screenshot_analysis.get("has_screenshot", False):
        screenshot_ratio = 0.0
    elif screenshot_analysis.get("blank_screenshot_count", 0) > 0:
        screenshot_ratio -= 0.35
    elif screenshot_analysis.get("duplicate_within_submission", False):
        screenshot_ratio -= 0.25

    if screenshot_analysis.get("duplicate_across_submissions"):
        screenshot_ratio -= 0.25
    screenshot_ratio = max(0.0, min(1.0, screenshot_ratio))

    positive_score = (
        (settings.marks_completeness_weight * completeness_ratio)
        + (settings.marks_execution_weight * execution_ratio)
        + (settings.marks_theory_weight * theory_ratio)
        + (settings.marks_relevance_weight * relevance)
        + (settings.marks_screenshot_weight * screenshot_ratio)
    )
    plagiarism_penalty = settings.marks_plagiarism_penalty_weight * plagiarism_score
    ai_penalty = settings.marks_ai_penalty_weight * ai_generated_score
    final_score_hundred = max(0.0, min(100.0, positive_score - plagiarism_penalty - ai_penalty))
    final_score_five = final_score_hundred / 20

    return {
        "marks": round(final_score_five, 2),
        "score_out_of_5": round(final_score_five, 2),
        "score_out_of_100": round(final_score_hundred, 2),
        "plagiarism_level": _plagiarism_level(plagiarism_score),
        "components": {
            "completeness_ratio": round(completeness_ratio, 4),
            "execution_ratio": round(execution_ratio, 4),
            "theory_ratio": round(theory_ratio, 4),
            "relevance_ratio": round(relevance, 4),
            "screenshot_ratio": round(screenshot_ratio, 4),
            "plagiarism_penalty": round(plagiarism_penalty, 4),
            "ai_generated_penalty": round(ai_penalty, 4),
        },
        "weights": {
            "completeness": settings.marks_completeness_weight,
            "execution": settings.marks_execution_weight,
            "theory": settings.marks_theory_weight,
            "relevance": settings.marks_relevance_weight,
            "screenshot": settings.marks_screenshot_weight,
            "plagiarism_penalty": settings.marks_plagiarism_penalty_weight,
            "ai_penalty": settings.marks_ai_penalty_weight,
        },
        "present_sections": present_sections,
        "missing_sections": [section for section in REQUIRED_SECTIONS if section not in present_sections],
    }
