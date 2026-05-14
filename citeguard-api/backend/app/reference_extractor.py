from __future__ import annotations

import re
from typing import Iterable

from .models import ParsedReference


DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
LEADING_MARKER_RE = re.compile(r"^\s*(\[\d+\]|［\d+］|【\d+】|\(\d+\)|（\d+）|\d+[\).、．])\s*")
QUOTED_TITLE_RE = re.compile(r'"([^"]{8,})"|“([^”]{8,})”')
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
REFERENCE_TYPE_RE = re.compile(r"[\[［][JMDCPNR][\]］]", re.IGNORECASE)
CJK_RE = re.compile(r"[\u3400-\u9fff]")


def parse_reference_paragraphs(paragraphs: Iterable[str]) -> list[ParsedReference]:
    entries = split_reference_entries(paragraphs)
    return [parse_reference_entry(entry) for entry in entries if entry.strip()]


def split_reference_entries(paragraphs: Iterable[str]) -> list[str]:
    entries: list[str] = []
    current: list[str] = []

    for paragraph in paragraphs:
        text = paragraph.strip()
        if not text:
            continue

        starts_new = bool(LEADING_MARKER_RE.match(text))
        if starts_new and current:
            entries.append(" ".join(current))
            current = []

        current.append(LEADING_MARKER_RE.sub("", text))

    if current:
        entries.append(" ".join(current))

    return entries


def parse_reference_entry(text: str) -> ParsedReference:
    doi = extract_doi(text)
    year = extract_year(text)
    authors = extract_authors(text, year)
    title = extract_title(text, year)
    venue = extract_venue(text, title)

    return ParsedReference(
        original_text=text,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
    )


def extract_doi(text: str) -> str | None:
    match = DOI_RE.search(text)
    if not match:
        return None
    return match.group(0).rstrip(".,;。；，、").lower()


def extract_year(text: str) -> str | None:
    cleaned = URL_RE.sub("", DOI_RE.sub("", text))
    years = list(YEAR_RE.finditer(cleaned))
    for match in years:
        before = cleaned[match.start() - 1] if match.start() > 0 else ""
        after = cleaned[match.end()] if match.end() < len(cleaned) else ""
        if before == "-" or after == "-":
            continue
        tail = cleaned[match.end() :].lstrip()
        if not tail or tail[0] in ".,;:)。，；：、":
            return match.group(0)
    return years[-1].group(0) if years else None


def extract_authors(text: str, year: str | None) -> list[str]:
    quoted = QUOTED_TITLE_RE.search(text)
    if quoted:
        author_blob = text[: quoted.start()]
    elif contains_cjk(text):
        author_blob = split_reference_sentences(text)[0]
    else:
        boundary = text.find(year) if year and year in text else -1
        author_blob = text[:boundary] if boundary > 0 else text.split(".")[0]

    author_blob = author_blob.strip(" .")
    if not author_blob:
        return []

    author_blob = author_blob.replace(" et al", "").replace("等", "")
    parts = re.split(r"\s*[,，、]\s*|\s+and\s+|;\s*|；\s*", author_blob)
    authors = [part.strip() for part in parts if len(part.strip()) > 1]
    return authors[:8]


def extract_title(text: str, year: str | None) -> str | None:
    cleaned = DOI_RE.sub("", text)
    quoted = QUOTED_TITLE_RE.search(cleaned)
    if quoted:
        return (quoted.group(1) or quoted.group(2)).strip(" .,")

    if contains_cjk(cleaned):
        title = extract_cjk_title(cleaned, year)
        if title:
            return title

    if year and year in cleaned:
        after_year = cleaned.split(year, 1)[1]
        candidate = first_sentence(after_year)
        if candidate:
            return candidate

    sentences = re.split(r"\.\s+", cleaned)
    for sentence in sentences[1:]:
        candidate = sentence.strip(" .")
        if len(candidate) > 12 and not YEAR_RE.search(candidate):
            return candidate
    return None


def extract_venue(text: str, title: str | None) -> str | None:
    if not title or title not in text:
        return None
    after_title = text.split(title, 1)[1]
    after_title = REFERENCE_TYPE_RE.sub("", after_title, count=1)
    after_title = after_title.lstrip('",” .。；;，, ')

    if contains_cjk(text):
        year_match = YEAR_RE.search(after_title)
        if year_match:
            venue = after_title[: year_match.start()].strip(" .。；;，,")
            return venue[:120] if venue else None

    parts = [part.strip(" .。；;，,") for part in re.split(r"\.\s+|。", after_title) if part.strip(" .。；;，,")]
    if not parts:
        return None
    venue = parts[0]
    return venue[:120] if venue else None


def first_sentence(text: str) -> str | None:
    text = text.strip(" .。；;，,")
    if not text:
        return None
    sentence = re.split(r"\.\s+|。", text, maxsplit=1)[0].strip(" .。；;，,")
    return sentence if len(sentence) > 12 else None


def extract_cjk_title(text: str, year: str | None) -> str | None:
    marker = REFERENCE_TYPE_RE.search(text)
    if marker:
        before_marker = text[: marker.start()].strip(" .。；;，,")
        segments = split_reference_sentences(before_marker)
        candidate = last_non_year_segment(segments)
        if candidate:
            return clean_cjk_title(candidate)

    segments = split_reference_sentences(text)
    if len(segments) >= 3 and year and segments[1] == year:
        return clean_cjk_title(segments[2])
    if len(segments) >= 2:
        return clean_cjk_title(segments[1])

    if year and year in text:
        after_year = text.split(year, 1)[1]
        candidate = first_sentence(after_year)
        if candidate:
            return clean_cjk_title(candidate)

    return None


def split_reference_sentences(text: str) -> list[str]:
    return [part.strip(" .。；;，,") for part in re.split(r"\.\s+|。", text) if part.strip(" .。；;，,")]


def last_non_year_segment(segments: list[str]) -> str | None:
    for segment in reversed(segments):
        if segment and not YEAR_RE.fullmatch(segment):
            return segment
    return None


def clean_cjk_title(text: str) -> str | None:
    title = REFERENCE_TYPE_RE.sub("", text).strip(" .。；;，,")
    title = re.sub(r"^(19|20)\d{2}\s*[.。；;，,]\s*", "", title)
    return title if len(title) >= 4 else None


def contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))
