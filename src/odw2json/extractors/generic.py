"""The extractor for a document type that has only field rules in its configuration.

Each field rule has these keys:
- path: the place of the value in the JSON, for example "faktura.kwota".
- kind: text, date, amount, account, nip, krs, regon, pesel, email, number or regex.
- labels: a list of regular expressions. The value comes after the first label that occurs.
- pattern: for kind "regex", a regular expression with one group.
- override: if true, the rule replaces a value of the dedicated extractor. The default is false.
"""

from __future__ import annotations

import re

from odw2json import common
from odw2json.classify import DocType

KINDS = {
    "date": common.first_date,
    "amount": common.parse_amount,
    "account": lambda s: (common.find_accounts(s) or [(0, None)])[0][1],
    "email": common.find_email,
    "number": lambda s: (re.search(r"\d+", s) or [None])[0],
}
LABELLED = {"nip": "NIP", "krs": "KRS", "regon": "REGON", "pesel": "PESEL"}


def find_value(text: str, rule: dict) -> tuple[object, str | None]:
    kind = rule.get("kind", "text")
    if kind == "regex":
        m = re.search(rule["pattern"], text, re.IGNORECASE | re.MULTILINE)
        return (common.normalize_spaces(m.group(1)), m.group(0)) if m else (None, None)
    for label in rule.get("labels", []):
        m = re.search(rf"(?:{label})\s*[:\-]?\s*(.*(?:\n.*)?)", text, re.IGNORECASE | re.MULTILINE)
        if not m:
            continue
        rest = m.group(1)
        if kind == "text":
            value = rest.split("\n")[0].strip() or rest.split("\n")[-1].strip()
        elif kind in LABELLED:
            value = common.labelled_number(m.group(0), LABELLED[kind], {"regon": (14, 9), "pesel": 11}.get(kind, 10))
        else:
            value = KINDS[kind](rest)
        if value not in (None, ""):
            return value, m.group(0).strip()
    return None, None


def set_path(data: dict, path: str, value) -> None:
    keys = path.split(".")
    for key in keys[:-1]:
        data = data.setdefault(key, {})
    data[keys[-1]] = value


def get_path(data: dict, path: str):
    for key in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def apply_fields(text: str, fields: list[dict], data: dict, evidence: dict[str, str]) -> None:
    for rule in fields:
        if get_path(data, rule["path"]) is not None and not rule.get("override", False):
            continue
        value, source = find_value(text, rule)
        if value is not None:
            set_path(data, rule["path"], value)
            evidence[rule["path"]] = source


def extract(text: str, doc_type: DocType, evidence: dict[str, str]) -> dict:
    data = doc_type.empty()
    apply_fields(text, doc_type.fields, data, evidence)
    return data
