"""PDF extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pdfplumber
from PIL import Image
from PyPDF2 import PdfReader

from app.evaluation.section_detector import SectionDetectionResult, detect_sections


@dataclass(slots=True)
class ExtractedImage:
    """Embedded image extracted from a PDF."""

    name: str
    image: Image.Image
    width: int
    height: int


@dataclass(slots=True)
class ExtractedDocument:
    """Normalized PDF extraction result."""

    text: str
    page_count: int
    images: list[ExtractedImage]
    metadata: dict[str, Any]
    sections: dict[str, str]
    headings: list[dict[str, object]]


def _color_mode(color_space: Any) -> str:
    color_space = _resolve_pdf_object(color_space)
    if isinstance(color_space, list) and color_space:
        color_space = _resolve_pdf_object(color_space[0])
    if str(color_space) == "/DeviceCMYK":
        return "CMYK"
    if str(color_space) == "/DeviceRGB":
        return "RGB"
    return "L"


def _resolve_pdf_object(value: Any) -> Any:
    """Resolve nested PyPDF2 indirect objects into concrete values."""
    while hasattr(value, "get_object"):
        try:
            value = value.get_object()
        except Exception:
            break
    return value


def _image_from_xobject(x_object: Any, data: bytes) -> Image.Image | None:
    x_object = _resolve_pdf_object(x_object)
    try:
        return Image.open(BytesIO(data)).convert("RGB")
    except Exception:
        width = int(x_object.get("/Width", 0))
        height = int(x_object.get("/Height", 0))
        if not width or not height:
            return None

        mode = _color_mode(x_object.get("/ColorSpace"))
        try:
            return Image.frombytes(mode, (width, height), data).convert("RGB")
        except Exception:
            return None


def _extract_images(reader: PdfReader) -> list[ExtractedImage]:
    images: list[ExtractedImage] = []
    for page_number, page in enumerate(reader.pages):
        resources = _resolve_pdf_object(page.get("/Resources"))
        if not hasattr(resources, "get"):
            continue

        x_objects = _resolve_pdf_object(resources.get("/XObject"))
        if not hasattr(x_objects, "items"):
            continue

        for image_name, x_object_ref in x_objects.items():
            x_object = _resolve_pdf_object(x_object_ref)
            if not hasattr(x_object, "get"):
                continue
            if x_object.get("/Subtype") != "/Image":
                continue

            try:
                raw_data = x_object.get_data()
            except Exception:
                continue

            image = _image_from_xobject(x_object, raw_data)
            if image is None:
                continue

            images.append(
                ExtractedImage(
                    name=f"page_{page_number + 1}_{str(image_name).lstrip('/')}",
                    image=image,
                    width=image.width,
                    height=image.height,
                )
            )
    return images


def extract_document(file_path: str | Path, include_images: bool = True) -> ExtractedDocument:
    """Extract textual and embedded-image content from a PDF."""
    path = Path(file_path)
    text_fragments: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text_fragments.append(page.extract_text() or "")

    reader = PdfReader(str(path))
    text = "\n\n".join(fragment for fragment in text_fragments if fragment).strip()
    section_result: SectionDetectionResult = detect_sections(text)

    return ExtractedDocument(
        text=text,
        page_count=len(reader.pages),
        images=_extract_images(reader) if include_images else [],
        metadata=dict(reader.metadata or {}),
        sections=section_result.sections,
        headings=section_result.headings,
    )
