from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class ReferenceStatus(str, Enum):
    verified = "verified"
    mismatch = "mismatch"
    unverified = "unverified"
    likely_fabricated = "likely_fabricated"


class ParsedReference(BaseModel):
    original_text: str
    title: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    year: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None


class EvidenceSource(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    result: str
    url: Optional[HttpUrl] = None
    score: Optional[float] = None


class ReferenceFinding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    original_text: str
    status: ReferenceStatus
    confidence: float = Field(ge=0, le=1)
    title: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    year: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    evidence: list[EvidenceSource] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ReferenceCheckReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_name: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    references: list[ReferenceFinding]
