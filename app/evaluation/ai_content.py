"""Lightweight heuristic AI-generated content analysis."""

from __future__ import annotations

import math
import re
from statistics import pstdev

from app.models.enums import SimilarityLevel
from app.utils.config import get_settings

settings = get_settings()

COMMON_AI_PHRASES = (
    "in conclusion",
    "it is important to note",
    "overall",
    "furthermore",
    "moreover",
    "additionally",
    "in summary",
    "this demonstrates",
    "this highlights",
    "on the other hand",
)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+|\n+", text or "") if sentence.strip()]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _risk_level(score: float) -> SimilarityLevel:
    if score >= settings.ai_generated_threshold_high:
        return SimilarityLevel.HIGH
    if score >= settings.ai_generated_threshold_medium:
        return SimilarityLevel.MEDIUM
    return SimilarityLevel.LOW


def detect_ai_generated_content(text: str) -> dict[str, object]:
    """Estimate AI-generated writing risk using transparent heuristics."""
    tokens = _tokenize(text)
    sentences = _sentences(text)
    if len(tokens) < 80 or len(sentences) < 3:
        return {
            "score": 0.0,
            "level": SimilarityLevel.LOW,
            "features": {
                "token_count": len(tokens),
                "sentence_count": len(sentences),
                "reason": "insufficient_text",
            },
        }

    sentence_lengths = [len(_tokenize(sentence)) for sentence in sentences if sentence.strip()]
    mean_sentence_length = sum(sentence_lengths) / max(len(sentence_lengths), 1)
    sentence_length_variation = pstdev(sentence_lengths) if len(sentence_lengths) > 1 else 0.0
    consistency_score = 1.0 - min(1.0, sentence_length_variation / max(mean_sentence_length, 1.0))

    type_token_ratio = len(set(tokens)) / max(len(tokens), 1)
    repetition_score = _clamp((0.48 - type_token_ratio) / 0.22)

    phrase_hits = sum((text or "").lower().count(phrase) for phrase in COMMON_AI_PHRASES)
    phrase_density = phrase_hits / max(len(sentences), 1)
    phrase_score = _clamp(phrase_density / 0.35)

    long_sentence_ratio = sum(length >= 24 for length in sentence_lengths) / max(len(sentence_lengths), 1)
    structure_score = _clamp(long_sentence_ratio / 0.55)

    punctuation_density = len(re.findall(r"[,;:]", text or "")) / max(len(tokens), 1)
    punctuation_score = _clamp((0.015 - punctuation_density) / 0.015)

    score = _clamp(
        (0.30 * consistency_score)
        + (0.22 * repetition_score)
        + (0.20 * phrase_score)
        + (0.18 * structure_score)
        + (0.10 * punctuation_score)
    )

    return {
        "score": round(score, 4),
        "level": _risk_level(score),
        "features": {
            "token_count": len(tokens),
            "sentence_count": len(sentences),
            "mean_sentence_length": round(mean_sentence_length, 2),
            "sentence_length_variation": round(sentence_length_variation, 2),
            "type_token_ratio": round(type_token_ratio, 4),
            "common_ai_phrase_hits": phrase_hits,
            "long_sentence_ratio": round(long_sentence_ratio, 4),
            "punctuation_density": round(punctuation_density, 4),
        },
    }
