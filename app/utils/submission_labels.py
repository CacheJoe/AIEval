"""Helpers for deriving human-friendly submission labels from filenames."""

from __future__ import annotations

from pathlib import Path
import re

IGNORED_FILENAME_TOKENS = {
    "lab",
    "labs",
    "experiment",
    "experiments",
    "exp",
    "assignment",
    "assignments",
    "report",
    "reports",
    "submission",
    "submissions",
    "practical",
    "practicals",
    "final",
    "draft",
    "copy",
    "pdf",
}
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def derive_submitter_label(filename: str, explicit_label: str | None = None) -> str:
    """Create a clean display label for a submission."""
    if explicit_label and explicit_label.strip():
        return explicit_label.strip()

    stem = Path(filename).stem.strip()
    email_match = EMAIL_PATTERN.search(stem)
    if email_match:
        stem = email_match.group(0).split("@", 1)[0]

    raw_tokens = re.findall(r"[A-Za-z0-9]+", stem)
    filtered_tokens = [
        token
        for token in raw_tokens
        if token.lower() not in IGNORED_FILENAME_TOKENS
    ]

    if not filtered_tokens:
        return Path(filename).stem or filename

    return " ".join(token.capitalize() for token in filtered_tokens[:6])

