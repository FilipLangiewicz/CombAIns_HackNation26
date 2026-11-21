"""Extractors. Each module has extract(text, doc_type, evidence) -> dict.

The module name is in the "extractor" key of the type configuration.
"""

from __future__ import annotations

import importlib

from odw2json.classify import DocType
from odw2json.extractors import generic


def extract(text: str, doc_type: DocType) -> tuple[dict, dict[str, str]]:
    """Give the data and the evidence: for each field path, the source text of the value."""
    evidence: dict[str, str] = {}
    module = importlib.import_module(f"odw2json.extractors.{doc_type.extractor}")
    data = module.extract(text, doc_type, evidence)
    # Field rules in the configuration add new fields or replace a value without a change of the code.
    if doc_type.extractor != "generic" and doc_type.fields:
        generic.apply_fields(text, doc_type.fields, data, evidence)
    return data, evidence
