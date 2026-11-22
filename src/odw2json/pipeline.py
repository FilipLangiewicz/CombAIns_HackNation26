"""Process one PDF file: read the text, find the type and extract the data."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from odw2json import ocr, validate
from odw2json.classify import classify
from odw2json.extractors import extract
from odw2json.pdftext import read_pdf


@dataclass
class Result:
    path: Path
    doc_type: str | None
    data: dict
    evidence: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)  # the values that the validation removed
    scores: dict[str, float] = field(default_factory=dict)
    ocr_pages: list[int] = field(default_factory=list)
    ocr_missing: bool = False
    text: str = ""
    page_count: int = 0
    ocr_retry: bool = False  # a second OCR with a higher resolution ran
    skipped_pages: list[int] = field(default_factory=list)


def process_text(text: str, path: Path = Path("text")) -> Result:
    found = classify(text)
    result = Result(Path(path), None, {}, scores=found.scores, text=text)
    if found.doc_type is not None:
        result.doc_type = found.doc_type.name
        result.data, result.evidence = extract(text, found.doc_type)
        result.warnings = validate.apply(result.data, found.doc_type.raw.get("validate", []))
    return result


def key_field_empty(data: dict, paths: list[str]) -> bool:
    """True if a key field is empty or missing. "[]" in a path means each item of a list."""
    for path in paths:
        found = list(validate.locate(data, path.split("."), ""))
        if not found or any(parent.get(key) is None for parent, key, _ in found):
            return True
    return False


def fill_empty(first, second):
    """Keep each value of the first result. Take a value of the second result only for an empty field."""
    if isinstance(first, dict) and isinstance(second, dict):
        return {k: fill_empty(first.get(k), second.get(k)) if k in first else second[k] for k in {**first, **second}}
    if isinstance(first, list):
        return first if first else second
    return second if first is None else first


def found_type(result: Result):
    from odw2json.classify import load_types

    return next(t for t in load_types() if t.name == result.doc_type)


def weak(result: Result) -> bool:
    """No type, or a key field of the type is empty. The key fields are in "ocr_retry_if_empty" of the type."""
    if result.doc_type is None:
        # A document far below each minimum score is of another kind. A second OCR costs time and gives nothing.
        from odw2json.classify import load_types

        return any(result.scores.get(t.name, 0) >= t.min_score / 2 for t in load_types())
    return key_field_empty(result.data, found_type(result).raw.get("ocr_retry_if_empty", []))


def process_pdf(path: Path) -> Result:
    doc = read_pdf(path)
    result = process_text(doc.text, path)
    if doc.skipped_pages and result.doc_type and not found_type(result).raw.get("ocr_first_pages_only", False):
        # The type can have data on the last pages, for example the signatures: read all pages.
        doc = read_pdf(path, max_ocr_pages=None)
        result = process_text(doc.text, path)
    paths = found_type(result).raw.get("ocr_more_pages_if_empty", []) if result.doc_type else []
    if doc.skipped_pages and key_field_empty(result.data, paths):
        # Some fields are empty and some scanned pages had no OCR: read all pages and fill only the empty fields.
        full = process_text(read_pdf(path, max_ocr_pages=None).text, path)
        if full.doc_type == result.doc_type:
            result.data = fill_empty(result.data, full.data)
            result.evidence = full.evidence | result.evidence
            doc.ocr_pages = sorted(set(doc.ocr_pages + doc.skipped_pages))
    if doc.ocr_pages and ocr.RETRY_DPI > ocr.DPI and weak(result):
        # A bad scan: read the scanned pages again with a higher resolution. Keep each value of the first result.
        sharp = process_text(read_pdf(path, max_ocr_pages=len(doc.ocr_pages), dpi=ocr.RETRY_DPI).text, path)
        if result.doc_type is None and sharp.doc_type is not None:
            result = sharp
        elif sharp.doc_type == result.doc_type and result.doc_type is not None:
            result.data = fill_empty(result.data, sharp.data)
            result.evidence = sharp.evidence | result.evidence
            result.warnings += validate.apply(result.data, found_type(result).raw.get("validate", []))
        result.ocr_retry = True
    result.ocr_pages, result.ocr_missing = doc.ocr_pages, doc.ocr_missing
    result.page_count = len(doc.pages)
    result.skipped_pages = [p for p in doc.skipped_pages if p not in doc.ocr_pages]
    return result
