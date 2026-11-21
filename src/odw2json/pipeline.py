"""Process one PDF file: read the text, find the type and extract the data."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from odw2json.classify import classify
from odw2json.extractors import extract
from odw2json.pdftext import read_pdf


@dataclass
class Result:
    path: Path
    doc_type: str | None
    data: dict
    evidence: dict[str, str] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    ocr_pages: list[int] = field(default_factory=list)
    ocr_missing: bool = False
    text: str = ""


def process_pdf(path: Path) -> Result:
    doc = read_pdf(path)
    found = classify(doc.text)
    result = Result(Path(path), None, {}, scores=found.scores, ocr_pages=doc.ocr_pages, ocr_missing=doc.ocr_missing)
    result.text = doc.text
    if found.doc_type is not None:
        result.doc_type = found.doc_type.name
        result.data, result.evidence = extract(doc.text, found.doc_type)
    return result
