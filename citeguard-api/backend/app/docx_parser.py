from __future__ import annotations

from pathlib import Path

from docx import Document


REFERENCE_HEADINGS = {
    "references",
    "bibliography",
    "works cited",
    "参考文献",
    "引用文献",
}


def extract_reference_paragraphs(docx_path: Path) -> list[str]:
    document = Document(docx_path)
    paragraphs = [normalize_space(p.text) for p in document.paragraphs]
    paragraphs = [p for p in paragraphs if p]

    start_index = find_reference_heading(paragraphs)
    if start_index is None:
        return paragraphs[-80:]

    tail = paragraphs[start_index + 1 :]
    return [p for p in tail if not looks_like_next_section(p)]


def find_reference_heading(paragraphs: list[str]) -> int | None:
    for index, paragraph in enumerate(paragraphs):
        key = paragraph.strip().lower().rstrip(":")
        if key in REFERENCE_HEADINGS:
            return index
    return None


def looks_like_next_section(text: str) -> bool:
    lowered = text.strip().lower().rstrip(":")
    if lowered in {"appendix", "supplementary materials", "acknowledgements"}:
        return True
    return len(text) < 48 and text.isupper()


def normalize_space(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())
