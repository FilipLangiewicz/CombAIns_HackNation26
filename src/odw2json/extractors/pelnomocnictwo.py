"""The extractor for the type "pelnomocnictwo" (power of attorney).

The layout of the document changes from case to case. Thus the code does not use fixed sections.
It finds the identifiers (KRS, NIP), the legal forms, the titles of the attorneys and the roles of the signers.
"""

from __future__ import annotations

import difflib
import re

from odw2json import common
from odw2json.classify import DocType
from odw2json.ocr import fold

UP = "A-ZĄĆĘŁŃÓŚŹŻ"
LOW = "a-ząćęłńóśźż"
NAME_TOKEN = rf"[{UP}][{LOW}]+(?:-[{UP}][{LOW}]+)?"
NAME = rf"{NAME_TOKEN}\s+{NAME_TOKEN}"
IDENT = re.compile(r"\b(KRS|NIP|REGON)\b\s*[:.]?\s*(\d[\d\s-]{7,16}\d)", re.IGNORECASE)


def _alt(items: list[str]) -> str:
    return "|".join(f"(?:{i})" for i in items)


PESEL_AFTER = re.compile(r"PESEL[^\d]{0,30}?(\d{11})\b")


def find_attorneys(text: str, cfg: dict, evidence: dict[str, str], signers: set[str] = frozenset()) -> list[dict]:
    titles = _alt(cfg["titles"])
    candidates: list[tuple[int, int, str, str]] = []  # (start, end, name, source)
    for m in re.finditer(rf"(?<![{LOW}])(?:{titles})\s+({NAME})", text):
        candidates.append((m.start(), m.end(), m.group(1), m.group(0)))
    # The title after the name: "Pani Annie Nowak, adwokat, PESEL ...".
    masc, fem = common.first_names()
    for m in re.finditer(rf"({NAME})(?:,\s*| |\s*\(\s*|[ \t]*[–—-][ \t]*)(?:{titles})(?![{LOW}])", text):
        known = common.to_nominative(m.group(1)).split()[0] in masc | fem  # not "Kancelaria Adwokacka adw."
        if known and not any(s <= m.start(1) < e for s, e, _, _ in candidates):
            candidates.append((m.start(), m.end(), m.group(1), m.group(0)))
    # A PESEL in parentheses after the name: "Anna Nowak (pracownik Mocodawcy, PESEL: 68091502944)".
    for m in re.finditer(rf"({NAME})\s*\([^()]{{0,60}}PESEL", text):
        known = common.to_nominative(m.group(1)).split()[0] in masc | fem
        if known and not any(s <= m.start(1) < e for s, e, _, _ in candidates):
            candidates.append((m.start(), m.end(1), m.group(1), m.group(0)))
    # A form: the name on one line and the profession on the next line.
    for m in re.finditer(rf"({NAME})[ \t]*\n[ \t]*(?:Zawód|Tytuł zawodowy)\s*:", text):
        candidates.append((m.start(), m.end(), m.group(1), m.group(0)))
    # Only an attorney has a number in the register of the bar. This rule helps when the OCR loses the title.
    for m in re.finditer(rf"({NAME})\s*[(,]\s*(?:nr\s+wpisu|wpis\s+na\s+listę)", text):
        if not any(s <= m.start(1) < e for s, e, _, _ in candidates):
            candidates.append((m.start(), m.end(), m.group(1), m.group(0)))
    # A list of names after "udziela pełnomocnictwa:", one name on each line.
    for block in re.finditer(r"(?i:udziela\w*|ustanawia\w*)\s+(?i:pełnomocnictw\w*|pełnomocnik\w*)\s*:[ \t]*\n", text):
        for line in re.finditer(r"[ \t]*(?:\d+[.)]|[-–•])?[ \t]*([^\n]*)\n?", text[block.end() :]):
            m = re.match(rf"({NAME})(?=[ \t]*(?:\(|,|[–—-]|$))", line.group(1))
            if not m or not line.group(1):
                break
            start = block.end() + line.start(1)
            if common.to_nominative(m.group(1)).split()[0] in masc | fem and not any(
                s <= start < e for s, e, _, _ in candidates
            ):
                candidates.append((start, start + len(m.group(1)), m.group(1), line.group(1).strip()))
    if not candidates:
        # No title: use a name after "Pan" or "Pani" or after the heading of the attorney.
        label = rf"(?:Pani?|Pana|Panu|Panią|Pełnomocnik\w*:?)\s+({NAME})"
        for m in re.finditer(label, text):
            # Without a title, "Pan" or "Pani" can also name the signer of the principal.
            if common.to_nominative(m.group(1)) not in signers:
                candidates.append((m.start(), m.end(), m.group(1), m.group(0)))
    candidates.sort()
    found: dict[str, dict] = {}
    for i, (_, end, raw, src) in enumerate(candidates):
        name = common.to_nominative(common.strip_titles(raw))
        limit = candidates[i + 1][0] if i + 1 < len(candidates) else len(text)
        pesel = PESEL_AFTER.search(text[end : min(limit, end + 140)])
        item = found.setdefault(name, {"imie_nazwisko": name, "pesel": None, "src": src})
        if pesel and not item["pesel"]:
            item["pesel"], item["pesel_src"] = pesel.group(1), common.normalize_spaces(pesel.group(0))
    out = []
    for i, item in enumerate(found.values()):
        evidence[f"pelnomocnicy[{i}].imie_nazwisko"] = common.normalize_spaces(item.pop("src"))
        if item["pesel"]:
            evidence[f"pelnomocnicy[{i}].pesel"] = item.pop("pesel_src")
        out.append(item)
    return out


def identifier_clusters(text: str, cfg: dict) -> list[dict]:
    """Group the labelled identifiers of one company.

    A new group starts when a label repeats or when the gap has the legal form of another company.
    """
    forms = re.compile(rf"(?<![{LOW}{UP}])(?:{_alt(cfg.get('legal_forms', []))})")
    clusters: list[dict] = []
    current: dict | None = None
    last_end = 0
    for m in IDENT.finditer(text):
        label = m.group(1).upper()
        value = common.digits(m.group(2))
        gap = text[last_end : m.start()]
        if current is None or label in current["ids"] or ";" in gap or len(gap) > 150 or forms.search(gap):
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


def clean_name(name: str) -> str:
    """Remove a descriptive prefix that is not part of the name."""
    return re.sub(r"^(?:Wspólnicy\s+)?spółki\s+cywilnej\s+|^Spółka\s+cywilna\s+", "", name, flags=re.IGNORECASE)


def is_stop_word(word: str, stop: set[str]) -> bool:
    """A stop word after OCR errors: "MOCODAWCA·", "Pehnomocnictwo"."""
    letters = fold(re.sub(rf"[^{LOW}{UP}a-zA-Z]", "", word)).lower()
    if len(letters) < 6:
        return False
    return any(difflib.SequenceMatcher(None, letters, fold(s).lower()).ratio() >= 0.85 for s in stop if len(s) >= 6)


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
    for k, word in enumerate(reversed(words)):
        if word == "i" and name and k + 1 < len(words) and re.match(rf"^[{UP}]", words[-k - 2]):
            name.append(word)  # "Kowalski i Nowak s.c."
            continue
        if (
            word in stop
            or is_stop_word(word, stop)
            or not re.match(rf"^[{UP}\d]", word)
            or re.search(r"[,:;)(.]$", word)
        ):
            break
        # The OCR can split a stop word: "PELNOMOCNI CTWO".
        if k + 1 < len(words) and words[-k - 2] + word in stop:
            break
        name.append(word)
    if not name:
        return None
    full = " ".join(reversed(name)) + " " + common.normalize_spaces(last.group(0))
    return clean_name(full), last.end()


def find_declarant(text: str) -> re.Match | None:
    return re.search(rf"niżej\s+podpisan\w*(?:\s*/\s*\w{{1,3}}|\(\w{{1,3}}\))?\s+({NAME})\s*,", text)


def declarant_is_legal(text: str, m: re.Match, cfg: dict) -> bool:
    """The declarant acts for a company ("działająca jako Prezes spółki Y"), not for himself."""
    tail = text[m.end() : m.end() + 400]
    own_firm = re.search(r"pod\s+(?:firmą|nazwą)\s", tail)
    cut = tail[: own_firm.start()] if own_firm else tail
    forms = re.search(rf"(?<![{LOW}{UP}])(?:{_alt(cfg.get('legal_forms', []))})", cut)
    return bool(re.search(r"\bKRS\b", cut) or (forms and not re.match(r"s\.\s?c\.", forms.group(0))))


def find_person_principal(text: str, m: re.Match) -> dict:
    """A natural person who runs a business: "Ja, niżej podpisany Jan Kowalski, ... pod firmą X, ul. ..."."""
    firm = re.search(r"pod\s+(?:firmą|nazwą)\s+(.+?),\s*(?:ul\.|al\.|pl\.|os\.|\d)", text[m.end() :], re.DOTALL)
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


PRINCIPAL_HEADING_RE = re.compile(r"[ \t]*(?:(?:Za|W\s+imieniu)\s+)?Mocodaw\w*[ \t]*:?[ \t]*", re.IGNORECASE)


def find_signers(text: str, cfg: dict) -> list[tuple[int, str, str]]:
    """Find the persons who sign: a name with a role, or a name under a signature line."""
    role = rf"(?i:(?:(?:Funkcja|Stanowisko)\s*:\s*)?(?:{_alt(cfg['roles'])}))\b"
    name_end = rf"(?:^|.*\s)({NAME})"
    lines = []  # (position, text) of each line without the leading signature dots
    pos = 0
    for raw in text.split("\n"):
        # A page footer or a place for the stamp can stand between the name and the role.
        footer = r"\s*(?:Strona\s+\d+\s*(?:z|/)\s*\d+|\(?podpis\)?|\(?(?:miejsce\s+na\s+)?piecz[ęe][ćc](?:\s+firmow\w*)?(?:\s+i\s+podpis)?\)?)\s*"
        if not re.fullmatch(footer, raw, re.IGNORECASE):
            stamp = re.match(r"\s*\(?(?:miejsce\s+na\s+)?piecz[ęe][ćc]\s+firmow\w*\)?\s+", raw, re.IGNORECASE)
            cut = stamp.end() if stamp else 0
            lines.append((pos + cut, raw[cut:].lstrip(" \t._…·•-")))
        pos += len(raw) + 1
    accepted = re.search(r"przyjmuj", text)
    limit = accepted.start() if accepted else len(text)

    titles = re.compile(rf"(?:{_alt(cfg['titles'])})\s*$", re.IGNORECASE)

    def valid(name: str) -> bool:
        return not re.match(role, name) and not re.search(r"\b(?:sp|S)\.", name)

    def attorney(m: re.Match) -> bool:
        # In two signature columns, the OCR can put the role of the signer under the name of the attorney.
        return bool(titles.search(m.string[: m.start(1)]))

    found: list[tuple[int, str, str]] = []
    dots_before = False
    for i, (pos, line) in enumerate(lines):
        has_dots = bool(re.match(r"^[ \t]*[._…]{4,}", text[pos : pos + 60])) or dots_before
        nxt = lines[i + 1][1] if i + 1 < len(lines) else ""
        same = re.fullmatch(rf"{name_end}[ \t]*(?:[,–—-][ \t]*)?{role}.*", line)
        split = re.fullmatch(rf"{name_end}[ \t]*", line) if re.match(role, nxt) else None
        alone = has_dots and pos < limit and re.fullmatch(rf"({NAME})", line)
        pair = re.fullmatch(rf"({NAME})\s+({NAME})\s*", line)
        roles_below = [ln for _, ln in lines[i + 1 : i + 3] if len(re.findall(role, ln)) >= 2]
        if pair and roles_below and valid(pair.group(1)) and valid(pair.group(2)):
            # Two signature blocks side by side: two names on one line, two roles on a line below.
            for name in pair.group(1, 2):
                found.append((pos, common.to_nominative(name), common.normalize_spaces(line + " " + roles_below[0])))
        elif same:
            # A line can have more than one signer: "A B – Prezes oraz C D – Członek Zarządu".
            each = list(re.finditer(rf"({NAME})[ \t]*[,–—-][ \t]*{role}", line)) or [same]
            for m in each:
                if valid(m.group(1)) and not attorney(m):
                    found.append((pos, common.to_nominative(m.group(1)), common.normalize_spaces(line)))
        else:
            m = split or alone
            if m and valid(m.group(1)) and not attorney(m):
                found.append(
                    (
                        pos,
                        common.to_nominative(m.group(1)),
                        common.normalize_spaces(line + " " + (nxt if split else "")),
                    )
                )
        # Keep the flag over the line "Za <company>" that can stand between the dots and the name.
        dots_before = (has_dots and not line) or (has_dots and bool(re.match(r"(?:Za|W imieniu)\b", line)))
        # A heading of the signature block of the principal: "Mocodawca:", "Za Mocodawcę:".
        dots_before = dots_before or bool(PRINCIPAL_HEADING_RE.fullmatch(line))
    # The prose can name the signers: "my, Jan Nowak (Prezes Zarządu)" or "przez Prokurenta Jana Nowaka".
    before = _alt(cfg.get("roles_before_name", []))
    prose = [rf"({NAME})\s*\(\s*{role}\s*\)", rf"przez\s*:?\s+({NAME})\s*[–—-]\s*{role}"]
    prose += [rf"(?<![{LOW}])(?:{before})\s+({NAME})"] if before else []
    for pattern in prose:
        for m in re.finditer(pattern, text[:limit]):
            name = common.to_nominative(m.group(1))
            masc, fem = common.first_names()
            known = name.split()[0] in masc | fem  # the prose has many capital words that are not names
            if known and valid(m.group(1)) and all(f[1] != name for f in found):
                found.append((m.start(), name, common.normalize_spaces(m.group(0))))
    return found


def find_name_without_legal_form(text: str, before: int) -> tuple[str, int] | None:
    """Find a company name that has no known legal form. The name stands before the address or the KRS."""
    window_start = max(before - 250, 0)
    # The anchor "Mocodawca" stays on its line: a heading "§ 1. Mocodawca" is not a part of the name below it.
    anchor = (
        r"(?:Mocodawc\w*(?:[ \t]+\d{1,2})?:?[ \t]+(?:jest[ \t]+)?|Nazwa(?:\s+\w+)?:\s*|imieniu\s+|reprezentacji\s+"
        r"|reprezentowania\s+|Za\s+|\d\)\s+|^(?!(?:Niniejszym|Działając|Ja|My|PEŁNOMOCNICTW\w*|Mocodaw\w*)\b))"
    )
    pattern = re.compile(
        rf"{anchor}([{UP}\d][^\n,;:()|]*?)(?=\s*(?:,|\(|\||z\s+siedzibą|KRS\b|NIP\b|\n)|[ \t]{{3,}})", re.MULTILINE
    )
    last = None
    for m in pattern.finditer(text, window_start, before):
        # A wrapped line can start with the postal code, the street or a sentence of the text.
        if not re.match(r"\d{2}-\d{3}|(?:ul|al|pl|os)\.", m.group(1)):
            last = m
    if last is None:
        return None
    return clean_name(common.normalize_spaces(last.group(1))), last.end()


def extract(text: str, doc_type: DocType, evidence: dict[str, str]) -> dict:
    data = doc_type.empty()
    cfg = doc_type.raw.get("extract", {})
    text = common.despace_caps(text)

    principals: list[dict] = []
    declarant = find_declarant(text)
    if declarant and not declarant_is_legal(text, declarant, cfg):
        person = find_person_principal(text, declarant)
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
        law_firm = re.compile(_alt(cfg.get("law_firm_words", [])) or r"(?!)")
        for cluster in identifier_clusters(text, cfg):
            with_form = find_company_name(text, cluster["start"], cfg)
            without_form = find_name_without_legal_form(text, cluster["start"])
            company = with_form or without_form
            if with_form and without_form and law_firm.search(with_form[0]) and without_form[1] > with_form[1]:
                company = without_form  # the law firm in the letterhead stands before the principal
            nazwa = company[0] if company else None
            principals.append(
                {
                    "data": {"imie_nazwisko": None, "krs": cluster["ids"].get("KRS"),
                             "nazwa": nazwa, "nip": cluster["ids"].get("NIP"),
                             "typ": "osoba_prawna"},
                    "podpisujacy": [],
                    "pos": cluster["start"],
                    "ev": {"krs": cluster["src"].get("KRS"), "nip": cluster["src"].get("NIP"),
                           "nazwa": nazwa, "typ": next(iter(cluster["src"].values()))},
                }
            )  # fmt: skip
            mark_natural_person(text, principals[-1])
        if any(not law_firm.search(p["data"]["nazwa"] or "") for p in principals):
            # The letterhead of the attorney can have the NIP of the law firm.
            principals = [p for p in principals if not law_firm.search(p["data"]["nazwa"] or "")]
        signers = find_signers(text, cfg)
        if declarant:  # the declarant signs for the company
            signers.insert(
                0,
                (
                    declarant.start(),
                    common.to_nominative(declarant.group(1)),
                    common.normalize_spaces(declarant.group(0)),
                ),
            )
        assign_signers(text, [p for p in principals if not p["podpisujacy"]], signers)

    for i, p in enumerate(principals):
        for key, value in p["data"].items():
            if value is not None:
                evidence[f"mocodawca[{i}].data.{key}"] = p["ev"][key]
        for j, s in enumerate(p["podpisujacy"]):
            evidence[f"mocodawca[{i}].podpisujacy[{j}].imie_nazwisko"] = s.pop("src", "")
        data["mocodawca"].append({"data": p["data"], "podpisujacy": p["podpisujacy"]})

    signer_names = {s["imie_nazwisko"] for p in data["mocodawca"] for s in p["podpisujacy"]}
    data["pelnomocnicy"] = find_attorneys(text, cfg, evidence, signer_names)
    return data


def mark_natural_person(text: str, principal: dict) -> None:
    """A business without a KRS can be a natural person. Its name ends with the name of the owner."""
    data = principal["data"]
    nazwa = data["nazwa"]
    if data["krs"] or not nazwa:
        return
    if re.search(r"\bs\.\s?c\.$", nazwa) or re.search(r"spółk\w*\s+cywiln", nazwa, re.IGNORECASE):
        data["typ"] = "osoba_fizyczna"  # the partners are the signers
        return
    tail = re.search(rf"({NAME})$", nazwa)
    if tail and len(re.findall(re.escape(tail.group(1)).replace(r"\ ", r"\s+"), text)) >= 2:
        data["typ"] = "osoba_fizyczna"
        data["imie_nazwisko"] = common.to_nominative(tail.group(1))
        principal["podpisujacy"] = [{"imie_nazwisko": data["imie_nazwisko"], "src": nazwa}]
        principal["ev"]["imie_nazwisko"] = nazwa


def assign_signers(text: str, principals: list[dict], signers: list[tuple[int, str, str]]) -> None:
    """Give each signer to the company that the text names last before the signature."""
    if not principals:
        return
    for pos, name, src in signers:
        owner = principals[0]
        # The description of a company can name its signer: "KRS ..., reprezentowana przez: Jan Nowak".
        named = [
            m
            for m in re.finditer(re.escape(name).replace(r"\ ", r"\s+"), text)
            if re.search(r"(?:reprezentowan\w*|przez)\s*:?[^.;]{0,80}$", text[max(m.start() - 100, 0) : m.start()])
        ]
        block_owner = None
        if named and len(principals) > 1:
            # The owner is the company that the text names last before "reprezentowana przez".
            best = -1
            for p in principals:
                marks = [p["pos"]] if p["pos"] < named[0].start() else []
                if p["data"]["nazwa"]:
                    pattern = re.escape(p["data"]["nazwa"]).replace(r"\ ", r"\s+")
                    marks += [m.start() for m in re.finditer(pattern, text[: named[0].start()])]
                if marks and max(marks) > best:
                    best, block_owner = max(marks), p
        if block_owner is not None:
            owner = block_owner
        elif len(principals) > 1:
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
