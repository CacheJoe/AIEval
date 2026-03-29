"""Plagiarism scoring."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.evaluation.relevance import semantic_similarity
from app.utils.config import get_settings

settings = get_settings()


@dataclass(slots=True)
class SimilarityEdge:
    """Pairwise similarity between two submissions."""

    source_submission_id: str
    target_submission_id: str
    tfidf_score: float
    ngram_score: float
    semantic_score: float
    combined_score: float


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _ngram_set(text: str, size: int = 5) -> set[str]:
    tokens = _tokenize(text)
    return {" ".join(tokens[index : index + size]) for index in range(max(0, len(tokens) - size + 1))}


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def compute_similarity_edges(documents: dict[str, str]) -> list[SimilarityEdge]:
    """Compute pairwise plagiarism edges for a batch of submissions."""
    submission_ids = list(documents.keys())
    texts = [documents[submission_id] for submission_id in submission_ids]
    if len(texts) < 2:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 3))
    tfidf_matrix = vectorizer.fit_transform(texts)
    cosine_matrix = cosine_similarity(tfidf_matrix)
    ngram_sets = {submission_id: _ngram_set(documents[submission_id]) for submission_id in submission_ids}

    edges: list[SimilarityEdge] = []
    for left_index, right_index in combinations(range(len(submission_ids)), 2):
        left_id = submission_ids[left_index]
        right_id = submission_ids[right_index]
        tfidf_score = float(cosine_matrix[left_index][right_index])
        ngram_score = _jaccard_similarity(ngram_sets[left_id], ngram_sets[right_id])
        semantic_score, _ = semantic_similarity(documents[left_id], documents[right_id])
        combined_score = (
            (settings.plagiarism_tfidf_weight * tfidf_score)
            + (settings.plagiarism_ngram_weight * ngram_score)
            + (settings.plagiarism_semantic_weight * semantic_score)
        )
        edges.append(
            SimilarityEdge(
                source_submission_id=left_id,
                target_submission_id=right_id,
                tfidf_score=round(tfidf_score, 4),
                ngram_score=round(ngram_score, 4),
                semantic_score=round(semantic_score, 4),
                combined_score=round(min(1.0, max(0.0, combined_score)), 4),
            )
        )
    return edges


def summarize_plagiarism(edges: list[SimilarityEdge]) -> dict[str, dict[str, object]]:
    """Summarize highest plagiarism risks per submission."""
    submission_summary: dict[str, dict[str, object]] = defaultdict(
        lambda: {"max_score": 0.0, "matches": []}
    )
    for edge in edges:
        for owner_id, peer_id in (
            (edge.source_submission_id, edge.target_submission_id),
            (edge.target_submission_id, edge.source_submission_id),
        ):
            peer_payload = {
                "peer_submission_id": peer_id,
                "combined_score": edge.combined_score,
                "tfidf_score": edge.tfidf_score,
                "ngram_score": edge.ngram_score,
                "semantic_score": edge.semantic_score,
            }
            summary = submission_summary[owner_id]
            summary["matches"].append(peer_payload)
            summary["max_score"] = max(float(summary["max_score"]), edge.combined_score)

    for value in submission_summary.values():
        value["matches"] = sorted(value["matches"], key=lambda item: item["combined_score"], reverse=True)[:5]
    return submission_summary

