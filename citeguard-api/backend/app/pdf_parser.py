from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from .docx_parser import find_reference_heading, looks_like_next_section, normalize_space
from .reference_extractor import LEADING_MARKER_RE


def extract_reference_paragraphs(pdf_path: Path) -> list[str]:
    text = extract_pdf_text(pdf_path)
    paragraphs = text_to_reference_like_paragraphs(text)
    paragraphs = [p for p in paragraphs if p]

    start_index = find_reference_heading(paragraphs)
    if start_index is None:
        return paragraphs[-120:]

    tail = paragraphs[start_index + 1 :]
    return [p for p in tail if not looks_like_next_section(p)]


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    page_text = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")
    return "\n".join(page_text)


def text_to_reference_like_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []

    for raw_line in text.splitlines():
        line = normalize_space(raw_line)
        if not line:
            continue

        if is_reference_heading(line):
            flush_current(paragraphs, current)
            current = []
            paragraphs.append(line)
            continue

        starts_new_reference = bool(LEADING_MARKER_RE.match(line))
        if starts_new_reference and current:
            flush_current(paragraphs, current)
            current = []

        if starts_new_reference or current:
            current.append(line)
        else:
            paragraphs.append(line)

    flush_current(paragraphs, current)
    return paragraphs


def is_reference_heading(line: str) -> bool:
    return find_reference_heading([line]) == 0


def flush_current(paragraphs: list[str], current: list[str]) -> None:
    if current:
        paragraphs.append(" ".join(current))
