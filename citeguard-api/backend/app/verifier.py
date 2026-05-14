from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Optional
from urllib.parse import quote

import httpx

from .models import EvidenceSource, ParsedReference, ReferenceFinding, ReferenceStatus
from .reference_extractor import contains_cjk

CNKI_URL_RE = re.compile(r"https?://[^\s<>()\"']*cnki\.[^\s<>()\"']+", re.IGNORECASE)


class ReferenceVerifier:
    def __init__(
        self,
        polite_email: Optional[str] = None,
        semantic_scholar_api_key: Optional[str] = None,
    ) -> None:
        self.polite_email = polite_email
        self.semantic_scholar_api_key = semantic_scholar_api_key

    async def verify_many(self, references: list[ParsedReference]) -> list[ReferenceFinding]:
        async with httpx.AsyncClient(timeout=12) as client:
            findings = []
            for reference in references:
                findings.append(await self.verify(reference, client))
            return findings

    async def verify(self, reference: ParsedReference, client: httpx.AsyncClient) -> ReferenceFinding:
        evidence: list[EvidenceSource] = []
        notes: list[str] = []

        crossref = await self.lookup_crossref(reference, client)
        if crossref:
            evidence.append(crossref["evidence"])
        else:
            evidence.append(EvidenceSource(name="Crossref", result="未找到匹配题录", score=0))

        openalex = await self.lookup_openalex(reference, client)
        if openalex:
            evidence.append(openalex["evidence"])

        best_catalog_score = max((item.score or 0 for item in evidence), default=0)
        if contains_cjk(reference.original_text) or not reference.doi or best_catalog_score < 0.88:
            semantic_scholar = await self.lookup_semantic_scholar(reference, client)
            if semantic_scholar:
                evidence.append(semantic_scholar["evidence"])

        cnki = self.lookup_cnki_assistive(reference)
        if cnki:
            evidence.append(cnki)

        best_score = max((item.score or 0 for item in evidence), default=0)
        status = self.status_from_evidence(reference, evidence)
        if status != ReferenceStatus.verified:
            notes.extend(self.build_notes(reference, evidence))

        return ReferenceFinding(
            original_text=reference.original_text,
            status=status,
            confidence=round(best_score, 2),
            title=reference.title,
            authors=reference.authors,
            year=reference.year,
            venue=reference.venue,
            doi=reference.doi,
            evidence=evidence,
            notes=notes,
        )

    async def lookup_crossref(
        self,
        reference: ParsedReference,
        client: httpx.AsyncClient,
    ) -> Optional[dict[str, Any]]:
        params: dict[str, str | int] = {"rows": 1}
        if self.polite_email:
            params["mailto"] = self.polite_email

        try:
            if reference.doi:
                url = f"https://api.crossref.org/works/{reference.doi}"
                response = await client.get(url, params={"mailto": self.polite_email} if self.polite_email else None)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                item = response.json()["message"]
            else:
                params["query.bibliographic"] = reference.original_text
                response = await client.get("https://api.crossref.org/works", params=params)
                response.raise_for_status()
                items = response.json()["message"].get("items", [])
                if not items:
                    return None
                item = items[0]
        except httpx.HTTPError:
            return {"evidence": EvidenceSource(name="Crossref", result="请求失败", score=0)}

        title = first(item.get("title"))
        doi = item.get("DOI")
        year = extract_crossref_year(item)
        score = score_match(reference, title, year, doi)
        result = "题录匹配" if score >= 0.86 else "找到题录但元数据不完全一致"
        if reference.doi and doi and normalize_doi(reference.doi) != normalize_doi(doi):
            result = "DOI 指向不一致"
            score = min(score, 0.45)

        return {
            "evidence": EvidenceSource(
                name="Crossref",
                result=result,
                url=f"https://doi.org/{doi}" if doi else None,
                score=score,
            )
        }

    async def lookup_openalex(
        self,
        reference: ParsedReference,
        client: httpx.AsyncClient,
    ) -> Optional[dict[str, Any]]:
        try:
            if reference.doi:
                response = await client.get(f"https://api.openalex.org/works/doi:{reference.doi}")
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                item = response.json()
            elif reference.title:
                response = await client.get("https://api.openalex.org/works", params={"search": reference.title, "per-page": 1})
                response.raise_for_status()
                results = response.json().get("results", [])
                if not results:
                    return None
                item = results[0]
            else:
                return None
        except httpx.HTTPError:
            return {"evidence": EvidenceSource(name="OpenAlex", result="请求失败", score=0)}

        title = item.get("display_name")
        year = str(item.get("publication_year")) if item.get("publication_year") else None
        doi = item.get("doi", "").replace("https://doi.org/", "")
        score = score_match(reference, title, year, doi)
        result = "题录匹配" if score >= 0.86 else "找到相近题录"
        if item.get("is_retracted"):
            result = "题录已标记撤稿"
            score = min(score, 0.7)

        return {
            "evidence": EvidenceSource(
                name="OpenAlex",
                result=result,
                url=item.get("id"),
                score=score,
            )
        }

    async def lookup_semantic_scholar(
        self,
        reference: ParsedReference,
        client: httpx.AsyncClient,
    ) -> Optional[dict[str, Any]]:
        if not reference.title:
            return None

        headers = {"x-api-key": self.semantic_scholar_api_key} if self.semantic_scholar_api_key else None
        params = {
            "query": reference.title,
            "limit": 1,
            "fields": "title,url,year,venue,externalIds,authors",
        }

        try:
            response = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            papers = response.json().get("data", [])
            if not papers:
                return None
            item = papers[0]
        except httpx.HTTPError:
            return {"evidence": EvidenceSource(name="Semantic Scholar", result="请求失败", score=0)}

        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI") or external_ids.get("doi")
        year = str(item.get("year")) if item.get("year") else None
        title = item.get("title")
        score = score_match(reference, title, year, doi)
        result = "题录匹配" if score >= 0.86 else "找到相近题录"

        return {
            "evidence": EvidenceSource(
                name="Semantic Scholar",
                result=result,
                url=item.get("url"),
                score=score,
            )
        }

    def lookup_cnki_assistive(self, reference: ParsedReference) -> Optional[EvidenceSource]:
        cnki_url = extract_cnki_url(reference.original_text)
        if cnki_url:
            return EvidenceSource(
                name="CNKI",
                result="文献中包含知网页面链接，可打开核对",
                url=cnki_url,
            )

        if reference.doi and "cnki" in reference.doi.lower():
            return EvidenceSource(
                name="CNKI",
                result="CNKI DOI，可通过 DOI 跳转核对",
                url=f"https://doi.org/{reference.doi}",
            )

        if contains_cjk(reference.original_text) and reference.title:
            return EvidenceSource(
                name="CNKI",
                result="知网检索入口（需在浏览器或机构账号中人工复核）",
                url=build_cnki_title_search_url(reference.title),
            )

        return None

    def status_from_evidence(
        self,
        reference: ParsedReference,
        evidence: list[EvidenceSource],
    ) -> ReferenceStatus:
        best = max((item.score or 0 for item in evidence), default=0)
        is_chinese_reference = contains_cjk(reference.original_text)
        if reference.doi and any("DOI 指向不一致" in item.result for item in evidence):
            return ReferenceStatus.mismatch
        if best >= 0.88:
            return ReferenceStatus.verified
        if is_chinese_reference and not reference.doi:
            return ReferenceStatus.unverified
        if best >= 0.55:
            return ReferenceStatus.mismatch
        if reference.doi:
            return ReferenceStatus.unverified
        return ReferenceStatus.likely_fabricated if best < 0.25 else ReferenceStatus.unverified

    def build_notes(self, reference: ParsedReference, evidence: list[EvidenceSource]) -> list[str]:
        notes: list[str] = []
        if not reference.doi:
            if contains_cjk(reference.original_text):
                notes.append("缺少 DOI；建议补充 CNKI、万方、维普、出版社页或原文 PDF 链接。")
            else:
                notes.append("缺少 DOI，建议补充出版社链接或原文 PDF。")
        if not reference.title:
            notes.append("未能稳定识别标题，可能需要人工复核。")
        if all((item.score or 0) == 0 for item in evidence):
            if contains_cjk(reference.original_text):
                notes.append("主要公开题录库未返回匹配结果；中文数据库覆盖有限，未命中不等于伪造。")
            else:
                notes.append("主要公开题录库未返回匹配结果。")
        return notes


def score_match(reference: ParsedReference, title: str | None, year: str | None, doi: str | None) -> float:
    score = 0.0
    weight = 0.0

    if reference.title and title:
        score += 0.7 * text_similarity(reference.title, title)
        weight += 0.7

    if reference.year and year:
        score += 0.15 * (1.0 if reference.year == year else 0.0)
        weight += 0.15

    if reference.doi and doi:
        score += 0.15 * (1.0 if normalize_doi(reference.doi) == normalize_doi(doi) else 0.0)
        weight += 0.15

    if weight == 0:
        return 0.0
    return round(score / weight, 3)


def text_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def normalize_text(value: str) -> str:
    punctuation = str.maketrans({
        ":": " ",
        "：": " ",
        "-": " ",
        "—": " ",
        "–": " ",
        "，": " ",
        "。": " ",
        "；": " ",
        "、": " ",
        "[": " ",
        "]": " ",
        "［": " ",
        "］": " ",
    })
    return " ".join(value.lower().translate(punctuation).split())


def normalize_doi(value: str) -> str:
    return value.lower().replace("https://doi.org/", "").strip()


def extract_cnki_url(text: str) -> Optional[str]:
    match = CNKI_URL_RE.search(text)
    if not match:
        return None
    return match.group(0).rstrip(".,;。；，、)")


def build_cnki_title_search_url(title: str) -> str:
    return f"https://kns.cnki.net/kns8s/defaultresult/index?kw={quote(title)}&korder=TI"


def first(values: Any) -> Optional[str]:
    if isinstance(values, list) and values:
        return str(values[0])
    if isinstance(values, str):
        return values
    return None


def extract_crossref_year(item: dict[str, Any]) -> Optional[str]:
    for key in ("published-print", "published-online", "issued"):
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            return str(parts[0][0])
    return None
