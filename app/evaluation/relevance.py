"""Semantic relevance scoring."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def _load_sentence_model():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(settings.semantic_model_name)
    except Exception:
        return None


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([text_a or "", text_b or ""])
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])


def semantic_similarity(text_a: str, text_b: str) -> tuple[float, str]:
    """Compute semantic similarity with a graceful lexical fallback."""
    if settings.relevance_engine == "tfidf":
        return max(0.0, min(1.0, _tfidf_similarity(text_a, text_b))), "tfidf"

    model = _load_sentence_model()
    if settings.relevance_engine == "sentence_transformer" and model is None:
        return max(0.0, min(1.0, _tfidf_similarity(text_a, text_b))), "tfidf_fallback"
    if model is None:
        return max(0.0, min(1.0, _tfidf_similarity(text_a, text_b))), "tfidf_fallback"

    embeddings = model.encode([text_a or "", text_b or ""], normalize_embeddings=True)
    score = float(np.dot(embeddings[0], embeddings[1]))
    return max(0.0, min(1.0, score)), "sentence_transformer"


def relevance_score(topic: str, content: str) -> dict[str, object]:
    """Compare experiment topic against submission content."""
    score, method = semantic_similarity(topic, content)
    return {"score": round(score, 4), "method": method}
