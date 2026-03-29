"""Section detection for lab reports."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from app.utils.config import get_settings

settings = get_settings()

SECTION_ALIASES: dict[str, list[str]] = {
    "experiment_title": ["experiment title", "title", "lab title", "problem statement"],
    "aim": ["aim", "objective", "objective of experiment", "purpose"],
    "theory": ["theory", "background", "concept", "introduction"],
    "algorithm": ["algorithm", "procedure", "steps", "methodology"],
    "dataset": ["dataset", "data set", "data description", "input data"],
    "implementation": ["implementation", "code", "program", "source code"],
    "output": ["output", "result", "results", "observation"],
    "analysis": ["analysis", "discussion", "inference", "interpretation"],
    "conclusion": ["conclusion", "summary", "learning outcome"],
}

REQUIRED_SECTIONS = [
    "experiment_title",
    "aim",
    "theory",
    "algorithm",
    "dataset",
    "implementation",
    "output",
    "analysis",
    "conclusion",
]


@dataclass(slots=True)
class SectionDetectionResult:
    """Detected sections and heading metadata."""

    sections: dict[str, str]
    headings: list[dict[str, object]]


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return " ".join(cleaned.split())


def _heading_score(line: str, alias: str) -> float:
    if line == alias:
        return 1.0
    if line.startswith(alias) or alias.startswith(line):
        return 0.95

    line_tokens = set(line.split())
    alias_tokens = set(alias.split())
    if alias_tokens and alias_tokens.issubset(line_tokens):
        return 0.92

    window = " ".join(line.split()[: min(5, len(line.split()))])
    return max(
        SequenceMatcher(None, line, alias).ratio(),
        SequenceMatcher(None, window, alias).ratio(),
    )


def _looks_like_heading(raw_line: str, normalized_line: str) -> bool:
    tokens = normalized_line.split()
    if not tokens:
        return False

    stripped = raw_line.strip()
    if len(tokens) <= 6:
        return True
    if stripped.endswith(":") or stripped.isupper():
        return True
    if ":" in stripped[:25]:
        return True
    return False


def _extract_title_from_heading(raw_heading: str) -> str:
    parts = raw_heading.split(":", 1)
    if len(parts) == 2 and parts[1].strip():
        return parts[1].strip()
    return raw_heading.strip()


def detect_sections(text: str) -> SectionDetectionResult:
    """Detect known report sections using fuzzy heading matching."""
    lines = [line.strip() for line in text.splitlines()]
    candidates: list[tuple[int, str, float, str]] = []

    for index, raw_line in enumerate(lines):
        normalized_line = _normalize(raw_line)
        if not normalized_line or len(normalized_line.split()) > 10:
            continue
        if not _looks_like_heading(raw_line, normalized_line):
            continue

        best_section = None
        best_score = 0.0
        for section_name, aliases in SECTION_ALIASES.items():
            for alias in aliases:
                score = _heading_score(normalized_line, _normalize(alias))
                if score > best_score:
                    best_section = section_name.strip()
                    best_score = score

        if best_section and best_score >= settings.section_heading_similarity_threshold:
            candidates.append((index, best_section, best_score, raw_line))

    deduped: list[tuple[int, str, float, str]] = []
    seen_sections: set[str] = set()
    for candidate in sorted(candidates, key=lambda item: item[0]):
        if candidate[1] not in seen_sections:
            deduped.append(candidate)
            seen_sections.add(candidate[1])

    sections: dict[str, str] = {}
    headings: list[dict[str, object]] = []

    if deduped:
        for position, (line_index, section_name, score, raw_heading) in enumerate(deduped):
            start = line_index + 1
            end = deduped[position + 1][0] if position + 1 < len(deduped) else len(lines)
            body = "\n".join(lines[start:end]).strip()
            if section_name == "experiment_title" and not body:
                body = _extract_title_from_heading(raw_heading)
            sections[section_name] = body
            headings.append(
                {
                    "section": section_name,
                    "heading": raw_heading,
                    "line_index": line_index,
                    "score": round(score, 4),
                }
            )
    else:
        sections["unstructured"] = text.strip()

    if "experiment_title" not in sections:
        first_non_empty = next((line for line in lines if line), "")
        if first_non_empty:
            sections["experiment_title"] = first_non_empty

    return SectionDetectionResult(sections=sections, headings=headings)
