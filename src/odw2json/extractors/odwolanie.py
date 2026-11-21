"""The extractor for the type "odwolanie".

The header of the appeal has the sections "Odwołujący", "Zamawiający" and "dotyczy". The code works
on the text in one line, because the PDF can wrap or join the lines of the header in any place.
The text of the first charge gives the contested action. The rules for the action are in the configuration.
"""

from __future__ import annotations

import re

from odw2json import common
from odw2json.classify import DocType

I = re.IGNORECASE
STREET = r"(?:ul\.|ulica|al\.|aleja|aleje|pl\.|plac|os\.|osiedle)\s"
SECTION_RE = re.compile(r"(?<!\w)(Odwołując\w*|Zamawiając\w*|Wykonawca\s+wybrany)\b[^:]{0,160}?:", I)
DOTYCZY_RE = re.compile(r"(?<!\w)dotyczy\s*:", I)
DOTYCZY_END_RE = re.compile(
    r"ODWOŁANIE\b|Wartość\s+zamówienia|Wpis\s+od|Działając|Prezes\s+Krajowej|Krajowa\s+Izba"
    r"|(?:Odwołując|Zamawiając)\w*\s*:",
)
IDS_RE = re.compile(r"(?:\b(?:KRS|NIP|REGON)\b\s*:?\s*\d[\d \-]*\d\s*,?\s*)+", I)
STREET_RE = re.compile(rf"(?<!\w){STREET}", I)
POSTAL_RE = re.compile(r"\d{2}-\d{3}\b")
ADDRESS_CUT_RE = re.compile(rf",?\s+{STREET}|,\s*\d{{2}}-\d{{3}}\s", I)
EMAIL_TOKEN_RE = re.compile(r"\S+@\S+")
PAGE_LINE_RE = re.compile(
    r"^[ \t]*(?:Str(?:ona|\.)?\s*\d+(?:\s+z\s+\d+)?|-\s*\d+\s*-|\d+\s*/\s*\d+)[ \t]*$", re.MULTILINE | I
)
WORD = r"[A-ZŁŚŻŹĆ][a-ząćęłńóśźż\-]+"
PLACE_DATE_RE = re.compile(
    rf"(?P<city>{WORD}(?:\s+{WORD}){{0,2}}),?\s+(?:(?i:dnia)\s+)?(?P<date>(?i:{common.DATE_RE.pattern}))\s*(?i:r\.|roku)?"
)


def flat(text: str) -> str:
    return common.normalize_spaces(text)


def _head(text: str) -> str:
    """Give the part of the text before the body of the appeal."""
    m = re.search(r"Działając\s+w\s+imieniu|wnoszę\s+odwołanie|wnoszę\s+o\s*:", text)
    return text[: m.start()] if m else text[:4000]


# --- sections of the header ------------------------------------------------------


def split_head(head: str) -> tuple[list[tuple[str, str]], str]:
    """Give the sections of the parties as (kind, text) and the text of the section "dotyczy"."""
    procurement = ""
    m = DOTYCZY_RE.search(head)
    if m:
        end = DOTYCZY_END_RE.search(head, m.end())
        procurement = head[m.end() : end.start() if end else len(head)]
        head = head[: m.start()] + " " + (head[end.start() :] if end else "")
    marks = list(SECTION_RE.finditer(head))
    sections = []
    for i, mark in enumerate(marks):
        word = mark.group(1).lower()
        kind = (
            "odwolujacy"
            if word.startswith("odwołując")
            else "zamawiajacy"
            if word.startswith("zamawiając")
            else "wybrany"
        )
        end = marks[i + 1].start() if i + 1 < len(marks) else len(head)
        sections.append((kind, head[mark.start() : end]))
    return sections, procurement


def split_entities(section: str) -> list[dict]:
    """Find the entities of a section. An entity is a name, an address and identifiers."""
    anchors = [(m.start(), m.end(), m.group(0)) for m in IDS_RE.finditer(section)]
    if not anchors:
        m = STREET_RE.search(section)
        anchors = [(len(section), len(section), "")] if m else []
    entities, start = [], 0
    for a_start, a_end, ids in anchors:
        segment = section[start:a_start]
        start = a_end
        m = STREET_RE.search(segment)
        if m:
            raw = segment[: m.start()]
        else:
            postal = POSTAL_RE.search(segment)
            if not postal:
                continue
            raw = segment[: postal.start()].rsplit(",", 1)[0]
        mails = list(EMAIL_TOKEN_RE.finditer(raw))
        if mails:
            raw = raw[mails[-1].end() :]
        lead, _, name = raw.rpartition(":") if ":" in raw else ("", "", raw)
        marker = list(re.finditer(r"\d+\)", lead))
        role = lead[marker[-1].end() :] if marker else lead
        name = re.sub(r"^\s*\d+\)\s*", "", name).strip(" ,;-")
        if name:
            entities.append({"name": common.normalize_spaces(name), "ids": ids, "role": role})
    return entities


def entity_fields(entity: dict) -> dict:
    ids = entity["ids"]
    return {
        "krs": common.find_krs(ids),
        "nazwa": entity["name"],
        "nip": common.find_nip(ids),
        "regon": common.find_regon(ids),
    }


# --- the attorney --------------------------------------------------------------------

FIRST_NAME_EXCEPTIONS = {"jerzy", "antoni", "ignacy", "walenty", "kuba", "barnaba", "kosma"}
IRREGULAR_FIRST_NAMES = {"jacka": "Jacek", "marka": "Marek", "darka": "Darek", "janka": "Janek"}


def to_nominative(name: str) -> str:
    """Change a name from the genitive or the accusative to the nominative with simple rules."""
    parts = name.split()
    if len(parts) < 2:
        return name
    first, last = parts[0], parts[-1]
    low = last.lower()
    new_last = common.to_nominative(last)
    masculine = low.endswith(("skiego", "ckiego", "dzkiego", "skiemu"))
    feminine = low.endswith(("skiej", "ckiej", "dzkiej", "ską", "cką")) or first.lower().endswith("ę")
    if not (masculine or feminine) and new_last == last:
        if first.lower().endswith(("y", "i")) and first.lower() not in FIRST_NAME_EXCEPTIONS:
            feminine = True
        elif first.lower().endswith("a") and low.endswith("a") and not low.endswith(("ska", "cka", "dzka")):
            masculine, new_last = True, last[:-1]
    if masculine:
        new_first = IRREGULAR_FIRST_NAMES.get(first.lower()) or (first.removesuffix("a"))
    elif feminine:
        new_first = first[:-1] + "a" if first.lower().endswith(("ę", "y", "i")) else first
    else:
        new_first = first
    return " ".join([new_first, *parts[1:-1], new_last])


def parse_attorney(section: str, evidence: dict[str, str]) -> dict | None:
    m = re.search(
        r"reprezentowan(?P<end>\w*)\s+przez\s*:?\s*(?P<names>.*?)(?=\s+adres\s+do\s+korespondencji|\s+tel\b|$)",
        section,
        I,
    )
    if not m:
        return None
    pn = {"imie_nazwisko": None, "nazwa": None, "mail": None}
    first = re.split(r",\s*(?=(?:r\.\s*pr\.|adw\.|radc|adwokat|apl\.|mec\.))", m.group("names"))[0]
    name = common.strip_titles(first)
    if name:
        if m.group("end").lower().endswith(("ego", "ej", "ych")):
            name = to_nominative(name)
        pn["imie_nazwisko"] = name
        evidence["Odwolujacy[0].pelnomocnik.imie_nazwisko"] = first
    after = section[m.end() :]
    a = re.match(r"\s*adres\s+do\s+korespondencji\s*:\s*(.*?)(?=\s+tel\b|\s+e-?mail\b|\S+@|$)", after, I)
    if a:
        address = a.group(1)
        cut = ADDRESS_CUT_RE.search(address)
        firm = (address[: cut.start()] if cut else address).strip(" ,;")
        if firm:
            pn["nazwa"] = firm
            evidence["Odwolujacy[0].pelnomocnik.nazwa"] = address
    mail = common.find_email(after)
    if mail:
        pn["mail"] = mail
        evidence["Odwolujacy[0].pelnomocnik.mail"] = mail
    return pn


# --- the header line with the town and the date -----------------------------------


def find_place_and_date(head: str) -> tuple[str | None, str | None, str | None]:
    """Find a line like "Gdańsk, dnia 3 września 2026 roku" or "Gdańsk 03.09.2026"."""
    for m in PLACE_DATE_RE.finditer(head):
        iso = common.parse_date(re.fullmatch(common.DATE_RE, m.group("date")))
        if not iso:
            continue
        words = m.group("city").split()
        # After a postal code, the first word is the town of an address.
        if len(words) > 1 and re.search(r"\d{2}-\d{3}\s*$", head[: m.start("city")]):
            words = words[1:]
        return " ".join(words), iso, m.group(0)
    return None, None, None


# --- the contested action ----------------------------------------------------------


def first_charge_texts(text: str) -> list[str]:
    """Give the texts that describe the first charge, from the most to the least exact."""
    texts = []
    m = re.search(r"polegających\s+na\s*:\s*(.*?)(?=\s2\)\s|\sZamawiający\s+w\s+dniu|\sZaskarżon)", text)
    if m:
        texts.append(m.group(1))
    m = re.search(r"wnoszę\s+o\s*:\s*(Zamawiający\s+w\s+dniu.*?\.)(?=\s|$)", text)
    if m:
        texts.append(m.group(1))
    m = re.search(r"Zamawiający\s+w\s+dniu\s.*?\.(?=\s)", text)
    if m:
        texts.append(m.group(0))
    m = re.search(r"Zarzut\s+nr\s+1\s*[–\-:.]?\s*(.*?)(?=\sZarzut\s+nr\s+2|$)", text)
    if m:
        texts.append(m.group(1))
    return [common.normalize_spaces(t) for t in texts]


def classify_action(texts: list[str], rules: list[dict]) -> tuple[int | None, str]:
    for text in texts:
        for rule in rules:
            if any(re.search(p, text, I) for p in rule["patterns"]):
                return int(rule["code"]), text
    return None, ""


def action_date(texts: list[str]) -> tuple[str | None, str]:
    for text in texts:
        m = re.search(r"w\s+dniu\s+(?P<d>[^.]*?\d{4})", text) or re.search(r"z\s+dnia\s+(?P<d>[^;.,]*?\d{4})", text)
        if m:
            dates = common.find_dates(m.group("d"))
            if dates:
                return dates[0][1], text
    for text in texts:
        dates = common.find_dates(text)
        if dates:
            return dates[0][1], text
    return None, ""


# --- the procurement ------------------------------------------------------------------


def parse_procurement(block: str, evidence: dict[str, str]) -> dict:
    block = common.normalize_spaces(block)
    out: dict = {}
    m = re.search(r"(\d{4})\s*/\s*BZP\s*(\d{8})(\s*/\s*\d{1,3})?", block, I)
    out["numer_bzp"] = f"{m.group(1)}/BZP{m.group(2)}{(m.group(3) or '').replace(' ', '')}" if m else None
    m = re.search(r"(\d{4})\s*/\s*S\s*(\d{3})\s*-\s*(\d{6})", block)
    ted = f"{m.group(3)}-{m.group(1)}" if m else None
    if ted is None:
        m = re.search(r"TED\D{0,40}(\d{6})\s*-\s*(\d{4})", block, I) or re.search(
            r"Dzienniku\s+Urzędowym\D{0,40}(\d{6})\s*-\s*(\d{4})", block, I
        )
        ted = f"{m.group(1)}-{m.group(2)}" if m else None
    out["numer_ted"] = ted
    m = re.search(r"(?:nr|numer|znak)\s+(?:referencyjny|sprawy|postępowania)(?:\s+sprawy)?\s*:?\s*([^\s,;]+)", block, I)
    out["numer_postepowania"] = m.group(1).rstrip(".") if m else None
    quotes = '„"“«'
    closing = '”"»'
    m = re.search(rf"pn\.?\s*[{quotes}](.+?)[{closing}]\s*(?:,|\.|$|\s+(?:nr|numer|znak))", block) or re.search(
        rf"[{quotes}](.+?)[{closing}]", block
    )
    out["tytul"] = m.group(1).strip() if m else None
    for key, value in out.items():
        if value:
            evidence[f"ZamowieniePubliczne.{key}"] = str(value)
    return out


def extract(text: str, doc_type: DocType, evidence: dict[str, str]) -> dict:
    data = doc_type.empty()
    text = common.despace_caps(text)
    text = PAGE_LINE_RE.sub("", text)
    text = flat(text)
    head = _head(text)
    sections, procurement = split_head(head)

    kio = data["OdwolanieKIO"]
    place, day, line = find_place_and_date(head)
    if day:
        kio["data"], kio["miejscowosc"] = day, place
        evidence["OdwolanieKIO.data"] = evidence["OdwolanieKIO.miejscowosc"] = line

    texts = first_charge_texts(text)
    code, source = classify_action(texts, doc_type.raw.get("action_rules", []))
    if code:
        kio["czynnosc_powod_id"] = code
        kio["czynnosc_opis"] = str(doc_type.raw["actions"][code])
        evidence["OdwolanieKIO.czynnosc_powod_id"] = source
    kio["czynnosc_dzien"], source = action_date(texts)
    if kio["czynnosc_dzien"]:
        evidence["OdwolanieKIO.czynnosc_dzien"] = source

    appellant_sections = [s for k, s in sections if k == "odwolujacy"]
    appellants = [e for s in appellant_sections for e in split_entities(s)]
    if appellants:
        leader = next((a for a in appellants if "lider" in a["role"].lower()), appellants[0])
        row = entity_fields(leader)
        attorney = parse_attorney(" ".join(appellant_sections), evidence)
        row["przez-pelnomocnika"] = 1 if attorney else 0
        row["pelnomocnik"] = attorney
        data["Odwolujacy"] = [row]
        evidence["Odwolujacy[0].nazwa"] = leader["name"]

    authorities = [e for k, s in sections if k == "zamawiajacy" for e in split_entities(s)]
    many = len(authorities) > 1
    for i, entity in enumerate(authorities):
        row = entity_fields(entity)
        row["prowadzacy_postepowanie"] = None
        if many:
            row["prowadzacy_postepowanie"] = 1 if re.search(r"\b(?:lider\w*|prowadząc\w*)\b", entity["role"], I) else 0
        data["Zamawiajacy"].append(row)
        evidence[f"Zamawiajacy[{i}].nazwa"] = entity["name"]

    data["ZamowieniePubliczne"].update(parse_procurement(procurement or head, evidence))
    return data
