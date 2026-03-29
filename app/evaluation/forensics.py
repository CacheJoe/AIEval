"""Screenshot/image forensics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from PIL import Image

from app.utils.config import get_settings

settings = get_settings()


def _average_hash(image: Image.Image, hash_size: int = 8) -> str:
    grayscale = image.convert("L").resize((hash_size, hash_size))
    pixels = np.asarray(grayscale, dtype=np.float32)
    threshold = pixels.mean()
    bits = pixels >= threshold
    return "".join("1" if bit else "0" for bit in bits.flatten())


def _hash_similarity(hash_a: str, hash_b: str) -> float:
    if not hash_a or not hash_b or len(hash_a) != len(hash_b):
        return 0.0
    matches = sum(left == right for left, right in zip(hash_a, hash_b))
    return matches / len(hash_a)


def _is_blank(image: Image.Image) -> bool:
    grayscale = np.asarray(image.convert("L"), dtype=np.float32)
    return float(grayscale.std()) <= settings.blank_image_variance_threshold


def analyze_screenshots(images_by_submission: dict[str, list[Image.Image]]) -> dict[str, dict[str, Any]]:
    """Detect missing, blank, and duplicate screenshots."""
    hashes_by_submission: dict[str, list[str]] = {}
    owners_by_hash: dict[str, list[str]] = defaultdict(list)

    for submission_id, images in images_by_submission.items():
        hashes: list[str] = []
        for image in images:
            image_hash = _average_hash(image)
            hashes.append(image_hash)
            owners_by_hash[image_hash].append(submission_id)
        hashes_by_submission[submission_id] = hashes

    analysis: dict[str, dict[str, Any]] = {}
    for submission_id, images in images_by_submission.items():
        hashes = hashes_by_submission[submission_id]
        blank_flags = [_is_blank(image) for image in images]

        duplicate_within = len(hashes) != len(set(hashes))
        duplicate_across: list[str] = []
        for image_hash in hashes:
            for other_submission_id in owners_by_hash[image_hash]:
                if other_submission_id != submission_id and other_submission_id not in duplicate_across:
                    duplicate_across.append(other_submission_id)

        analysis[submission_id] = {
            "has_screenshot": len(images) > 0,
            "blank_screenshot_count": sum(blank_flags),
            "duplicate_within_submission": duplicate_within,
            "duplicate_across_submissions": duplicate_across,
            "image_count": len(images),
        }
    return analysis

