"""The extractor for the type "pelnomocnictwo" (power of attorney).

The layout of the document changes from case to case. Thus the code does not use fixed sections.
It finds the identifiers (KRS, NIP), the legal forms, the titles of the attorneys and the roles of the signers.
"""

from __future__ import annotations

import re

from odw2json import common
from odw2json.classify import DocType

UP = "A-ZĄĆĘŁŃÓŚŹŻ"
LOW = "a-ząćęłńóśźż"
NAME_TOKEN = rf"[{UP}][{LOW}]+(?:-[{UP}][{LOW}]+)?"
NAME = rf"{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{1,2}}"
IDENT = re.compile(r"\b(KRS|NIP|REGON)\b\s*[:.]?\s*(\d[\d\s-]{7,16}\d)", re.IGNORECASE)


def _alt(items: list[str]) -> str:
    return "|".join(f"(?:{i})" for i in items)


def _snippet(text: str, start: int, end: int) -> str:
    return common.normalize_spaces(text[max(start - 20, 0) : end + 20])


def _nominative(name: str) -> str:
    # Only the unambiguous endings of a surname are changed.
    parts = name.split()
    if parts and re.search(r"(?:iego|iej|ią)$", parts[-1]):
        parts[-1] = common.to_nominative(parts[-1])
    return " ".join(parts)


def find_attorneys(text: str, cfg: dict, evidence: dict[str, str]) -> list[dict]:
    titles = _alt(cfg["titles"])
    pattern = re.compile(rf"(?<![{LOW}])(?:{titles})\s+({NAME})")
    matches = list(pattern.finditer(text))
    found: dict[str, dict] = {}
    for i, m in enumerate(matches):
        name = _nominative(common.strip_titles(m.group(1)))
        limit = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        tail = text[m.end() : min(limit, m.end() + 90)]
        pesel = re.search(r"PESEL\s*:?\s*(\d{11})\b", tail)
        item = found.setdefault(name, {"imie_nazwisko": name, "pesel": None, "src": m.group(0)})
        if pesel and not item["pesel"]:
            item["pesel"] = pesel.group(1)
    if not found:
        # No title: use a name after "Pan" or "Pani" or after the heading of the attorney.
        label = rf"(?:Pani?|Pana|Panu|Panią|Pełnomocnik\w*:?)\s+({NAME})"
        for m in re.finditer(label, text):
            name = _nominative(m.group(1))
            found.setdefault(name, {"imie_nazwisko": name, "pesel": None, "src": m.group(0)})
    out = []
    for i, item in enumerate(found.values()):
        evidence[f"pelnomocnicy[{i}].imie_nazwisko"] = common.normalize_spaces(item.pop("src"))
        if item["pesel"]:
            evidence[f"pelnomocnicy[{i}].pesel"] = "PESEL " + item["pesel"]
        out.append(item)
    return out


def identifier_clusters(text: str) -> list[dict]:
    """Group the labelled identifiers of one company. A new group starts when a label repeats."""
    clusters: list[dict] = []
    current: dict | None = None
    last_end = 0
    for m in IDENT.finditer(text):
        label = m.group(1).upper()
        value = common.digits(m.group(2))
        gap = text[last_end : m.start()]
        if current is None or label in current["ids"] or ";" in gap or len(gap) > 150:
            current = {"start": m.start(), "ids": {}}
            clusters.append(current)
        current["ids"][label] = value
        current["end"] = m.end()
        last_end = m.end()
    seen, unique = set(), []
    for c in clusters:
        key = c["ids"].get("NIP") or c["ids"].get("KRS")
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def find_company_name(text: str, before: int, cfg: dict) -> tuple[str, int] | None:
    """Find the last company name that ends before the position. A name ends with a legal form."""
    forms = re.compile(rf"(?<![{LOW}{UP}])(?:{_alt(cfg['legal_forms'])})")
    window_start = max(before - 220, 0)
    last = None
    for m in forms.finditer(text, window_start, before):
        last = m
    if last is None:
        return None
    stop = set(cfg["stop_words"])
    words = re.findall(r"\S+", text[window_start : last.start()])
    name: list[str] = []
    for word in reversed(words):
        if word in stop or not re.match(rf"^[{UP}\d]", word) or re.search(r"[,:;)(.]$", word):
            break
        name.append(word)
    if not name:
        return None
    full = " ".join(reversed(name)) + " " + common.normalize_spaces(last.group(0))
    return full, last.end()


def find_person_principal(text: str) -> dict | None:
    """A natural person who runs a business: "Ja, niżej podpisany Jan Kowalski, ... pod firmą X, ul. ..."."""
    m = re.search(rf"niżej\s+podpisan\w*\s+({NAME})\s*,", text)
    if not m:
        return None
    firm = re.search(r"pod\s+firmą\s+(.+?),\s*(?:ul\.|al\.|pl\.|os\.|\d)", text[m.end() :], re.DOTALL)
    ids = {i.group(1).upper(): common.digits(i.group(2)) for i in IDENT.finditer(text)}
    return {
        "name": _nominative(m.group(1)),
        "firm": common.normalize_spaces(firm.group(1)) if firm else None,
        "nip": ids.get("NIP"),
        "krs": ids.get("KRS"),
        "src": _snippet(text, m.start(), m.end()),
        "pos": m.start(),
    }


def find_signers(text: str, cfg: dict) -> list[tuple[int, str, str]]:
    """Find the pairs of a name and a role, for example "Jan Kowalski / Prezes Zarządu"."""
    roles = _alt(cfg["roles"])
    pattern = re.compile(
        rf"^[ \t]*({NAME})[ \t]*(?:\n[ \t]*|[,–—-][ \t]*)(?i:{roles})(?:[ \t]+\w+){{0,3}}[ \t]*$", re.MULTILINE
    )
    out = []
    for m in pattern.finditer(text):
        name = common.strip_titles(m.group(1))
        if re.fullmatch(NAME, name):
            out.append((m.start(), _nominative(name), common.normalize_spaces(m.group(0))))
    return out


def extract(text: str, doc_type: DocType, evidence: dict[str, str]) -> dict:
    data = doc_type.empty()
    cfg = doc_type.raw.get("extract", {})
    text = common.despace_caps(text)

    principals: list[dict] = []
    person = find_person_principal(text)
    if person:
        principals.append(
            {
                "data": {"imie_nazwisko": person["name"], "krs": person["krs"], "nazwa": person["firm"] or person["name"],
                         "nip": person["nip"], "typ": "osoba_fizyczna"},
                "podpisujacy": [{"imie_nazwisko": person["name"]}],
                "pos": person["pos"],
                "src": person["src"] or "",
            }
        )  # fmt: skip
    else:
        for cluster in identifier_clusters(text):
            company = find_company_name(text, cluster["start"], cfg)
            principals.append(
                {
                    "data": {"imie_nazwisko": None, "krs": cluster["ids"].get("KRS"),
                             "nazwa": company[0] if company else None, "nip": cluster["ids"].get("NIP"),
                             "typ": "osoba_prawna"},
                    "podpisujacy": [],
                    "pos": cluster["start"],
                    "src": _snippet(text, cluster["start"], cluster["end"]),
                }
            )  # fmt: skip
        assign_signers(text, principals, find_signers(text, cfg))

    for i, p in enumerate(principals):
        for key, value in p["data"].items():
            if value is not None:
                evidence[f"mocodawca[{i}].data.{key}"] = p["src"]
        for j, s in enumerate(p["podpisujacy"]):
            evidence[f"mocodawca[{i}].podpisujacy[{j}].imie_nazwisko"] = s.pop("src", "")
        data["mocodawca"].append({"data": p["data"], "podpisujacy": p["podpisujacy"]})

    data["pelnomocnicy"] = find_attorneys(text, cfg, evidence)
    return data


def assign_signers(text: str, principals: list[dict], signers: list[tuple[int, str, str]]) -> None:
    """Give each signer to the company that the text names last before the signature."""
    if not principals:
        return
    for pos, name, src in signers:
        owner = principals[0]
        if len(principals) > 1:
            best = -1
            for p in principals:
                nazwa = p["data"]["nazwa"]
                if not nazwa:
                    continue
                for m in re.finditer(re.escape(nazwa), text):
                    if best < m.start() < pos:
                        best, owner = m.start(), p
        if all(s["imie_nazwisko"] != name for s in owner["podpisujacy"]):
            owner["podpisujacy"].append({"imie_nazwisko": name, "src": src})
