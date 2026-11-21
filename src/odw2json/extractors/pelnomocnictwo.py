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
NAME = rf"{NAME_TOKEN}\s+{NAME_TOKEN}"
IDENT = re.compile(r"\b(KRS|NIP|REGON)\b\s*[:.]?\s*(\d[\d\s-]{7,16}\d)", re.IGNORECASE)


def _alt(items: list[str]) -> str:
    return "|".join(f"(?:{i})" for i in items)


def find_attorneys(text: str, cfg: dict, evidence: dict[str, str]) -> list[dict]:
    titles = _alt(cfg["titles"])
    pattern = re.compile(rf"(?<![{LOW}])(?:{titles})\s+({NAME})")
    matches = list(pattern.finditer(text))
    found: dict[str, dict] = {}
    for i, m in enumerate(matches):
        name = common.to_nominative(common.strip_titles(m.group(1)))
        limit = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        tail = text[m.end() : min(limit, m.end() + 90)]
        pesel = re.search(r"PESEL\s*:?\s*(\d{11})\b", tail)
        item = found.setdefault(name, {"imie_nazwisko": name, "pesel": None, "src": m.group(0)})
        if pesel and not item["pesel"]:
            item["pesel"], item["pesel_src"] = pesel.group(1), pesel.group(0)
    if not found:
        # No title: use a name after "Pan" or "Pani" or after the heading of the attorney.
        label = rf"(?:Pani?|Pana|Panu|Panią|Pełnomocnik\w*:?)\s+({NAME})"
        for m in re.finditer(label, text):
            name = common.to_nominative(m.group(1))
            found.setdefault(name, {"imie_nazwisko": name, "pesel": None, "src": m.group(0)})
    out = []
    for i, item in enumerate(found.values()):
        evidence[f"pelnomocnicy[{i}].imie_nazwisko"] = common.normalize_spaces(item.pop("src"))
        if item["pesel"]:
            evidence[f"pelnomocnicy[{i}].pesel"] = item.pop("pesel_src")
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
            current = {"start": m.start(), "ids": {}, "src": {}}
            clusters.append(current)
        current["ids"][label] = value
        current["src"][label] = common.normalize_spaces(m.group(0))
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
    ids, id_src = {}, {}
    for i in IDENT.finditer(text):
        label = i.group(1).upper()
        ids[label] = common.digits(i.group(2))
        id_src[label] = common.normalize_spaces(i.group(0))
    return {
        "name": common.to_nominative(m.group(1)),
        "firm": common.normalize_spaces(firm.group(1)) if firm else None,
        "nip": ids.get("NIP"),
        "krs": ids.get("KRS"),
        "src": common.normalize_spaces(m.group(0)),
        "firm_src": common.normalize_spaces("pod firmą " + firm.group(1)) if firm else None,
        "id_src": id_src,
        "pos": m.start(),
    }


def find_signers(text: str, cfg: dict) -> list[tuple[int, str, str]]:
    """Find the persons who sign: a name with a role, or a name under a signature line."""
    role = rf"(?i:{_alt(cfg['roles'])})\b"
    name_end = rf"(?:^|.*\s)({NAME})"
    lines = []  # (position, text) of each line without the leading signature dots
    pos = 0
    for raw in text.split("\n"):
        lines.append((pos, raw.lstrip(" \t._…-")))
        pos += len(raw) + 1
    accepted = re.search(r"przyjmuj", text)
    limit = accepted.start() if accepted else len(text)

    def valid(name: str) -> bool:
        return not re.match(role, name) and not re.search(r"\b(?:sp|S)\.", name)

    found: list[tuple[int, str, str]] = []
    dots_before = False
    for i, (pos, line) in enumerate(lines):
        has_dots = bool(re.match(r"^[ \t]*[._…]{4,}", text[pos : pos + 60])) or dots_before
        nxt = lines[i + 1][1] if i + 1 < len(lines) else ""
        same = re.fullmatch(rf"{name_end}[ \t]*(?:[,–—-][ \t]*)?{role}.*", line)
        split = re.fullmatch(rf"{name_end}[ \t]*", line) if re.match(role, nxt) else None
        alone = has_dots and pos < limit and re.fullmatch(rf"({NAME})", line)
        m = same or split or alone
        if m and valid(m.group(1)):
            found.append(
                (pos, common.to_nominative(m.group(1)), common.normalize_spaces(line + " " + (nxt if split else "")))
            )
        # Keep the flag over the line "Za <company>" that can stand between the dots and the name.
        dots_before = (has_dots and not line) or (has_dots and bool(re.match(r"(?:Za|W imieniu)\b", line)))
    return found


def find_name_without_legal_form(text: str, before: int) -> tuple[str, int] | None:
    """Find a company name that has no known legal form. The name stands before the address or the KRS."""
    window_start = max(before - 250, 0)
    anchor = r"(?:Mocodawc\w*:?\s+(?:jest\s+)?|imieniu\s+|reprezentacji\s+|Za\s+|\d\)\s+|^)"
    pattern = re.compile(rf"{anchor}([{UP}\d][^\n,;:()]*?)(?=\s*(?:,|\(|z\s+siedzibą|KRS\b|NIP\b|\n))", re.MULTILINE)
    last = None
    for m in pattern.finditer(text, window_start, before):
        last = m
    if last is None:
        return None
    return common.normalize_spaces(last.group(1)), last.end()


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
                "ev": {"imie_nazwisko": person["src"], "nazwa": person["firm_src"] or person["src"],
                       "krs": person["id_src"].get("KRS"), "nip": person["id_src"].get("NIP"), "typ": person["src"]},
            }
        )  # fmt: skip
    else:
        for cluster in identifier_clusters(text):
            company = find_company_name(text, cluster["start"], cfg) or find_name_without_legal_form(
                text, cluster["start"]
            )
            principals.append(
                {
                    "data": {"imie_nazwisko": None, "krs": cluster["ids"].get("KRS"),
                             "nazwa": company[0] if company else None, "nip": cluster["ids"].get("NIP"),
                             "typ": "osoba_prawna"},
                    "podpisujacy": [],
                    "pos": cluster["start"],
                    "ev": {"krs": cluster["src"].get("KRS"), "nip": cluster["src"].get("NIP"),
                           "nazwa": company[0] if company else None, "typ": next(iter(cluster["src"].values()))},
                }
            )  # fmt: skip
        assign_signers(text, principals, find_signers(text, cfg))

    for i, p in enumerate(principals):
        for key, value in p["data"].items():
            if value is not None:
                evidence[f"mocodawca[{i}].data.{key}"] = p["ev"][key]
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
                for m in re.finditer(re.escape(nazwa).replace(r"\ ", r"\s+"), text):
                    if best < m.start() < pos:
                        best, owner = m.start(), p
        if all(s["imie_nazwisko"] != name for s in owner["podpisujacy"]):
            owner["podpisujacy"].append({"imie_nazwisko": name, "src": src})
