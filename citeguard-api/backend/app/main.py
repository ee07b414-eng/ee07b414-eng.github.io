from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .docx_parser import extract_reference_paragraphs as extract_docx_reference_paragraphs
from .models import ReferenceCheckReport
from .pdf_parser import extract_reference_paragraphs as extract_pdf_reference_paragraphs
from .reference_extractor import parse_reference_paragraphs
from .verifier import ReferenceVerifier


app = FastAPI(title="CiteGuard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"name": "CiteGuard API", "status": "ok"}


@app.head("/", include_in_schema=False)
async def root_head() -> None:
    return None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/checks", response_model=ReferenceCheckReport)
async def create_check(file: UploadFile = File(...)) -> ReferenceCheckReport:
    if not file.filename or file_extension(file.filename) not in {".docx", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported.")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / safe_file_name(file.filename)
        path.write_bytes(await file.read())

        try:
            paragraphs = extract_document_reference_paragraphs(path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Could not read references from this file.") from exc

        parsed = parse_reference_paragraphs(paragraphs)
        if not parsed:
            raise HTTPException(status_code=422, detail="No references were detected.")

        verifier = ReferenceVerifier(
            polite_email=os.getenv("CITEGUARD_MAILTO"),
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
        )
        findings = await verifier.verify_many(parsed)

    return ReferenceCheckReport(file_name=file.filename, references=findings)


def safe_file_name(file_name: str) -> str:
    return Path(file_name).name.replace("/", "_").replace("\\", "_")


def file_extension(file_name: str) -> str:
    return Path(file_name).suffix.lower()


def extract_document_reference_paragraphs(path: Path) -> list[str]:
    suffix = file_extension(path.name)
    if suffix == ".docx":
        return extract_docx_reference_paragraphs(path)
    if suffix == ".pdf":
        return extract_pdf_reference_paragraphs(path)
    raise ValueError(f"Unsupported file type: {suffix}")
