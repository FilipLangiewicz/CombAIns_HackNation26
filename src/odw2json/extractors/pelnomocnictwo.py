"""The extractor for the type "pelnomocnictwo"."""

from __future__ import annotations

from odw2json.classify import DocType


def extract(text: str, doc_type: DocType, evidence: dict[str, str]) -> dict:
    return doc_type.empty()
