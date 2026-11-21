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


def entity_fields(entity: dict, path: str, evidence: dict[str, str]) -> dict:
    """Give the fields of a party. The source text of each field goes to the evidence under the path."""
    row = {"krs": None, "nazwa": entity["name"], "nip": None, "regon": None}
    evidence[f"{path}.nazwa"] = entity["name"]
    for field, label, length in (("krs", "KRS", 10), ("nip", "NIP", 10), ("regon", "REGON", (14, 9))):
        found = common.labelled(entity["ids"], label, length)
        if found:
            row[field], evidence[f"{path}.{field}"] = found
    return row


# --- the attorney --------------------------------------------------------------------


def parse_attorney(section: str, evidence: dict[str, str]) -> tuple[dict, str] | tuple[None, None]:
    """Give the attorney and the text "reprezentowany przez ..." that shows him."""
    m = re.search(
        r"reprezentowan(?P<end>\w*)\s+przez\s*:?\s*(?P<names>.*?)(?=\s+adres\s+do\s+korespondencji|\s+tel\b|$)",
        section,
        I,
    )
    if not m:
        return None, None
    pn = {"imie_nazwisko": None, "nazwa": None, "mail": None}
    first = re.split(r",\s*(?=(?:r\.\s*pr\.|adw\.|radc|adwokat|apl\.|mec\.))", m.group("names"))[0]
    name = common.strip_titles(first)
    if name:
        if m.group("end").lower().endswith(("ego", "ej", "ych")):
            name = common.to_nominative(name)
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
            evidence["Odwolujacy[0].pelnomocnik.nazwa"] = common.normalize_spaces(a.group(0)[: a.start(1)] + firm)
    mail = common.EMAIL_RE.search(after)
    if mail:
        pn["mail"] = mail.group(0).rstrip(".")
        label = re.search(r"e-?mail\s*:?\s*$", after[: mail.start()], I)
        evidence["Odwolujacy[0].pelnomocnik.mail"] = common.normalize_spaces(
            after[label.start() : mail.end()] if label else mail.group(0)
        )
    return pn, m.group(0)


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
    """Give the code and the words of the text that match the rule, with some text around them."""
    for text in texts:
        for rule in rules:
            for pattern in rule["patterns"]:
                m = re.search(pattern, text, I)
                if m:
                    return int(rule["code"]), text[max(m.start() - 60, 0) : m.end() + 60]
    return None, ""


def action_date(texts: list[str]) -> tuple[str | None, str]:
    for text in texts:
        m = re.search(r"w\s+dniu\s+(?P<d>[^.]*?\d{4})", text) or re.search(r"z\s+dnia\s+(?P<d>[^;.,]*?\d{4})", text)
        if m:
            dates = common.find_dates(m.group("d"))
            if dates:
                return dates[0][1], m.group(0)
    for text in texts:
        for m in common.DATE_RE.finditer(text):
            if common.parse_date(m):
                return common.parse_date(m), text[max(m.start() - 30, 0) : m.end()]
    return None, ""


# --- the procurement ------------------------------------------------------------------


def parse_procurement(block: str, evidence: dict[str, str]) -> dict:
    block = common.normalize_spaces(block)
    out: dict = {}
    sources: dict[str, str] = {}
    m = re.search(r"(\d{4})\s*/\s*BZP\s*(\d{8})(\s*/\s*\d{1,3})?", block, I)
    out["numer_bzp"] = f"{m.group(1)}/BZP{m.group(2)}{(m.group(3) or '').replace(' ', '')}" if m else None
    sources["numer_bzp"] = m.group(0) if m else ""
    m = re.search(r"(\d{4})\s*/\s*S\s*(\d{3})\s*-\s*(\d{6})", block)
    ted = f"{m.group(3)}-{m.group(1)}" if m else None
    if ted is None:
        m = re.search(r"TED\D{0,40}(\d{6})\s*-\s*(\d{4})", block, I) or re.search(
            r"Dzienniku\s+Urzędowym\D{0,40}(\d{6})\s*-\s*(\d{4})", block, I
        )
        ted = f"{m.group(1)}-{m.group(2)}" if m else None
    out["numer_ted"] = ted
    sources["numer_ted"] = m.group(0) if m else ""
    m = re.search(r"(?:nr|numer|znak)\s+(?:referencyjny|sprawy|postępowania)(?:\s+sprawy)?\s*:?\s*([^\s,;]+)", block, I)
    out["numer_postepowania"] = m.group(1).rstrip(".") if m else None
    sources["numer_postepowania"] = m.group(0) if m else ""
    quotes = '„"“«'
    closing = '”"»'
    m = re.search(rf"pn\.?\s*[{quotes}](.+?)[{closing}]\s*(?:,|\.|$|\s+(?:nr|numer|znak))", block) or re.search(
        rf"[{quotes}](.+?)[{closing}]", block
    )
    out["tytul"] = m.group(1).strip() if m else None
    sources["tytul"] = m.group(0).rstrip(" ,.") if m else ""
    for key, value in out.items():
        if value:
            evidence[f"ZamowieniePubliczne.{key}"] = sources[key]
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
        evidence["OdwolanieKIO.czynnosc_powod_id"] = evidence["OdwolanieKIO.czynnosc_opis"] = source
    kio["czynnosc_dzien"], source = action_date(texts)
    if kio["czynnosc_dzien"]:
        evidence["OdwolanieKIO.czynnosc_dzien"] = source

    appellant_sections = [s for k, s in sections if k == "odwolujacy"]
    appellants = [e for s in appellant_sections for e in split_entities(s)]
    if appellants:
        leader = next((a for a in appellants if "lider" in a["role"].lower()), appellants[0])
        row = entity_fields(leader, "Odwolujacy[0]", evidence)
        attorney, attorney_text = parse_attorney(" ".join(appellant_sections), evidence)
        row["przez-pelnomocnika"] = 1 if attorney else 0
        row["pelnomocnik"] = attorney
        # Without "reprezentowany przez" the decision comes from the start of the section of the appellant.
        evidence["Odwolujacy[0].przez-pelnomocnika"] = attorney_text or appellant_sections[0][:100].strip()
        data["Odwolujacy"] = [row]

    authorities = [e for k, s in sections if k == "zamawiajacy" for e in split_entities(s)]
    many = len(authorities) > 1
    for i, entity in enumerate(authorities):
        row = entity_fields(entity, f"Zamawiajacy[{i}]", evidence)
        row["prowadzacy_postepowanie"] = None
        if many:
            lead = re.search(r"\b(?:lider\w*|prowadząc\w*)\b", entity["role"], I)
            row["prowadzacy_postepowanie"] = 1 if lead else 0
            # Without a keyword, the decision comes from the name of the party.
            evidence[f"Zamawiajacy[{i}].prowadzacy_postepowanie"] = (
                common.normalize_spaces(entity["role"]) if entity["role"].strip() else entity["name"]
            )
        data["Zamawiajacy"].append(row)

    data["ZamowieniePubliczne"].update(parse_procurement(procurement or head, evidence))
    return data
