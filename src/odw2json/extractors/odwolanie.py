"""The extractor for the type "odwolanie".

The header of the appeal has the sections "Odwołujący", "Zamawiający" and "dotyczy". The text
of the first charge gives the contested action. The rules for the action are in the configuration.
"""

from __future__ import annotations

import re

from odw2json import common
from odw2json.classify import DocType

SECTION_RE = re.compile(r"^(Odwołując\w*|Zamawiając\w*|Wykonawca\s+wybrany|dotyczy)\b[^\n]*?(?::|$)", re.IGNORECASE)
END_RE = re.compile(
    r"^(?:Prezes\s+Krajowej|Krajowa\s+Izba|ODWOŁANIE\b|Wartość\s+zamówienia|Wpis\s+od|Strona\s+\d+)", re.IGNORECASE
)
ADDRESS_RE = re.compile(r"^(?:ul\.|al\.|aleja|pl\.|plac|os\.)\s|\d{2}-\d{3}\s")
IDS_RE = re.compile(r"\b(?:NIP|KRS|REGON)\b")
ROLE_RE = re.compile(r"^\s*\d+\)")
ADDRESS_CUT_RE = re.compile(r",\s*(?:ul\.|al\.|aleja|pl\.|plac|os\.)\s|,\s*\d{2}-\d{3}\s")
CITY_DATE_RE = re.compile(r"^(?P<city>[^\d\n,]{2,60}?),?\s+(?:dnia\s+)?(?P<date>\d[^\n]*?)\s*(?:r\.|roku)?$")


def _head(text: str) -> str:
    """Give the part of the text before the body of the appeal."""
    m = re.search(r"Działając\s+w\s+imieniu|wnoszę\s+odwołanie|wnoszę\s+o:", text)
    return text[: m.start()] if m else text[:4000]


# --- sections of the header ------------------------------------------------------


def split_sections(head: str) -> list[tuple[str, list[str]]]:
    """Give (kind, lines) for each section. The kind is odwolujacy, zamawiajacy, wybrany or dotyczy."""
    sections: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for raw in head.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = SECTION_RE.match(line)
        if m and not END_RE.match(line):
            word = m.group(1).lower()
            kind = (
                "odwolujacy" if word.startswith("odwołując")
                else "zamawiajacy" if word.startswith("zamawiając")
                else "wybrany" if word.startswith("wykonawca")
                else "dotyczy"
            )  # fmt: skip
            current = []
            sections.append((kind, current))
            rest = line[m.end() :].strip()
            if kind == "dotyczy" and rest:
                current.append(rest)
            if kind != "dotyczy" and not line.endswith(":") and ":" in line:
                rest = line.split(":", 1)[1].strip()
                if rest and not re.match(r"Konsorcjum", rest, re.IGNORECASE):
                    current.append(rest)
            continue
        if END_RE.match(line) and not line.lower().startswith("strona"):
            current = None
            continue
        if current is not None and not re.match(r"Strona\s+\d+", line):
            current.append(line)
    return sections


def split_entities(lines: list[str]) -> list[dict]:
    """Find the entities of a section. An entity is a name, an address and a line with identifiers."""
    entities: list[dict] = []
    pending: list[str] = []  # lines since the last entity
    role = ""
    for line in lines:
        if ROLE_RE.match(line) or line.endswith(":"):
            role = line
            pending = []
            continue
        if IDS_RE.search(line) and not re.match(r"^(?:reprezentowan|adres|tel)", line):
            name_lines = []
            for p in pending:
                if ADDRESS_RE.match(p):
                    break
                name_lines.append(p)
            if name_lines:
                entities.append({"name": common.normalize_spaces(" ".join(name_lines)), "ids": line, "role": role})
            pending = []
            continue
        pending.append(line)
    return entities


def representative_lines(lines: list[str]) -> list[str]:
    """Give the lines of the section from the line "reprezentowany przez" to the end."""
    for i, line in enumerate(lines):
        if re.match(r"reprezentowan\w+\s+przez", line, re.IGNORECASE):
            return lines[i:]
    return []


def parse_attorney(lines: list[str], evidence: dict[str, str]) -> dict:
    pn = {"imie_nazwisko": None, "nazwa": None, "mail": None}
    block = "\n".join(lines)
    m = re.match(
        r"reprezentowan\w+\s+przez\s*:\s*(.*?)(?=\nadres do korespondencji|\ntel\.|$)", block, re.IGNORECASE | re.DOTALL
    )
    if m:
        first = re.split(
            r",\s*(?=(?:r\.\s*pr\.|adw\.|radca|adwokat|apl\.|mec\.))", common.normalize_spaces(m.group(1))
        )[0]
        name = common.strip_titles(first)
        if name:
            pn["imie_nazwisko"] = name
            evidence["Odwolujacy[0].pelnomocnik.imie_nazwisko"] = first
    m = re.search(
        r"adres\s+do\s+korespondencji\s*:\s*(.*?)(?=\ntel\.|\n[\w.+\-]+@|$)", block, re.IGNORECASE | re.DOTALL
    )
    if m:
        address = common.normalize_spaces(m.group(1))
        cut = ADDRESS_CUT_RE.search(address)
        firm = (address[: cut.start()] if cut else address).strip(" ,;")
        if firm:
            pn["nazwa"] = firm
            evidence["Odwolujacy[0].pelnomocnik.nazwa"] = address
    mail = common.find_email(block)
    if mail:
        pn["mail"] = mail
        evidence["Odwolujacy[0].pelnomocnik.mail"] = mail
    return pn


def parties(sections, kind: str) -> list[dict]:
    found = []
    for k, lines in sections:
        if k == kind:
            for entity in split_entities(lines):
                found.append({**entity, "lines": lines})
    return found


def entity_fields(entity: dict) -> dict:
    ids = entity["ids"]
    return {
        "krs": common.find_krs(ids),
        "nazwa": entity["name"],
        "nip": common.find_nip(ids),
        "regon": common.find_regon(ids),
    }


# --- the header line with the town and the date -----------------------------------


def find_place_and_date(head: str) -> tuple[str | None, str | None, str | None]:
    for line in head.splitlines()[:60]:
        line = line.strip()
        m = CITY_DATE_RE.match(line)
        if not m:
            continue
        dm = common.DATE_RE.fullmatch(m.group("date").strip())
        if dm and common.parse_date(dm):
            return common.normalize_spaces(m.group("city")), common.parse_date(dm), line
    return None, None, None


# --- the contested action ----------------------------------------------------------


def first_charge_texts(text: str) -> list[str]:
    """Give the texts that describe the first charge, from the most to the least exact."""
    texts = []
    m = re.search(
        r"polegających\s+na\s*:\s*\n?(.*?)(?=\n\s*\d+\)|\n\s*Zamawiający\s+w\s+dniu|\n\s*Zaskarżon)", text, re.DOTALL
    )
    if m:
        texts.append(m.group(1))
    m = re.search(r"wnoszę\s+o\s*:\s*\n(\s*Zamawiający\s+w\s+dniu.*?\.)(?=\s|$)", text, re.DOTALL)
    if m:
        texts.append(m.group(1))
    m = re.search(r"Zamawiający\s+w\s+dniu\s.*?\.(?=\s)", text, re.DOTALL)
    if m:
        texts.append(m.group(0))
    m = re.search(r"Zarzut\s+nr\s+1\s*[–\-:.]?\s*(.*?)(?:\n\s*Zarzut\s+nr\s+2|$)", text, re.DOTALL)
    if m:
        texts.append(m.group(1))
    return [common.normalize_spaces(t) for t in texts]


def classify_action(texts: list[str], rules: list[dict]) -> tuple[int | None, str]:
    for text in texts:
        for rule in rules:
            if any(re.search(p, text, re.IGNORECASE) for p in rule["patterns"]):
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
    m = re.search(r"(\d{4})\s*/\s*BZP\s*(\d{8})(\s*/\s*\d{1,3})?", block, re.IGNORECASE)
    out["numer_bzp"] = f"{m.group(1)}/BZP{m.group(2)}{(m.group(3) or '').replace(' ', '')}" if m else None
    m = re.search(r"(\d{4})\s*/\s*S\s*(\d{3})\s*-\s*(\d{6})", block)
    ted = f"{m.group(3)}-{m.group(1)}" if m else None
    if ted is None:
        m = re.search(r"TED\D{0,40}(\d{6})\s*-\s*(\d{4})", block, re.IGNORECASE) or re.search(
            r"Dzienniku\s+Urzędowym\D{0,40}(\d{6})\s*-\s*(\d{4})", block, re.IGNORECASE
        )
        ted = f"{m.group(1)}-{m.group(2)}" if m else None
    out["numer_ted"] = ted
    m = re.search(
        r"(?:nr|numer|znak)\s+(?:referencyjny|sprawy|postępowania)(?:\s+sprawy)?\s*:?\s*([^\s,;]+)",
        block,
        re.IGNORECASE,
    )
    out["numer_postepowania"] = m.group(1).rstrip(".") if m else None
    m = re.search(r"pn\.?\s*[„\"“](.+?)[”\"]\s*(?:,|\.|$|\s+(?:nr|numer|znak))", block) or re.search(
        r"[„\"“](.+?)[”\"]", block
    )
    out["tytul"] = m.group(1).strip() if m else None
    for key, value in out.items():
        if value:
            evidence[f"ZamowieniePubliczne.{key}"] = str(value)
    return out


def extract(text: str, doc_type: DocType, evidence: dict[str, str]) -> dict:
    data = doc_type.empty()
    text = re.sub(
        r"^[ \t]*Strona\s+\d+(?:\s+z\s+\d+)?[ \t]*$", "", common.despace_caps(text), flags=re.MULTILINE | re.IGNORECASE
    )
    head = _head(text)
    sections = split_sections(head)

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

    appellants = parties(sections, "odwolujacy")
    if appellants:
        leader = next((a for a in appellants if "lider" in a["role"].lower()), appellants[0])
        row = entity_fields(leader)
        attorney_lines = representative_lines(leader["lines"])
        row["przez-pelnomocnika"] = 1 if attorney_lines else 0
        row["pelnomocnik"] = parse_attorney(attorney_lines, evidence) if attorney_lines else None
        data["Odwolujacy"] = [row]
        evidence["Odwolujacy[0].nazwa"] = leader["name"]

    authorities = parties(sections, "zamawiajacy")
    many = len(authorities) > 1
    for i, entity in enumerate(authorities):
        row = entity_fields(entity)
        row["prowadzacy_postepowanie"] = None
        if many:
            row["prowadzacy_postepowanie"] = 1 if re.search(r"lider|prowadz", entity["role"], re.IGNORECASE) else 0
        data["Zamawiajacy"].append(row)
        evidence[f"Zamawiajacy[{i}].nazwa"] = entity["name"]

    procurement = "\n".join(" ".join(lines) for k, lines in sections if k == "dotyczy") or head
    data["ZamowieniePubliczne"].update(parse_procurement(procurement, evidence))
    return data
