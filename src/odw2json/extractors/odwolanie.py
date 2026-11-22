"""The extractor for the type "odwolanie".

The header of the appeal has the sections "Odwołujący", "Zamawiający" and "dotyczy". The code works
on the text in one line, because the PDF can wrap or join the lines of the header in any place.
The text of the first charge gives the contested action. The rules for the action are in the configuration.
"""

from __future__ import annotations

import itertools
import re

from odw2json import common
from odw2json.classify import DocType

I = re.IGNORECASE
STREET = r"(?:ul\.|ulica|al\.|aleja|aleje|pl\.|plac|os\.|osiedle)(?:\s|(?=[A-ZŁŚŻŹĆ]))"  # the OCR can lose the space after "ul."
GAP = r"(?:\s*\([^()]{0,160}\)|[^:\d,;.()]{0,40}?)"
SECTION_RE = re.compile(
    rf"(?<![\w(])(?<!ełnomocnik )(?:(?P<odw>Odwołując\w*(?:\s+\d{{1,2}}\b)?|Wykonawc\w+\s*\(\s*Odwołując\w*\s*\)|Wykonawc\w+\s+wnosząc\w+\s+odwołanie"
    rf"|Wnosząc\w+\s+odwołanie)|(?P<zam>Zamawiając\w*(?:\s+\d{{1,2}}\b)?)|(?P<wyb>Wykonawca\s+wybrany)){GAP}\s*:"
    r"|(?<![\w(])(?:(?P<odw2>(?-i:Od))|(?P<zam2>(?-i:Przeciwko))|(?P<oth>(?-i:Do)))\s*:"
    r"|(?<![\w(])(?:(?P<odw3>(?:Działając\s+)?(?-i:W|w)\s+imieniu)(?=\s)(?!\s+pozostał)"
    r"|(?P<odw4>Odwołując\w*|Zamawiając\w*)(?=\s+Nazwa\s*:))",
    I,
)
DOTYCZY_RE = re.compile(r"(?<!\w)dotyczy\s*:", I)
DOTYCZY_END_RE = re.compile(
    r"ODWOŁANIE\b|Wartość\s+zamówienia|Wpis\s+od|Działając|Prezes\s+Krajowej|Krajowa\s+Izba"
    r"|(?:Odwołując|Zamawiając)\w*\s*:",
)
# A number does not take the next list number: "NIP 9990000002 2) Gmina Beta".
IDS_RE = re.compile(
    r"(?:(?:\b(?:nr|numer)\s+)?\b(?:KRS|NIP|REGON)\b\s*:?\s*(?:PL\s*)?\d(?:[\d\-]|\s(?!\d{1,2}\s*[.)]))*\d\s*[,;]?\s*)+",
    I,
)
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


# A heading of a party on its own line, without a colon: "ODWOŁUJĄCY", "I. Zamawiający", "Odwołujący –".
HEADING_LINE_RE = re.compile(
    r"^[ \t]*(?:[IVX]{1,4}\.|\d{1,2}[.)])?[ \t]*((?:Odwołując|Zamawiając)\w*(?:[ \t]+się)?)[ \t]*[–—-]?[ \t]*$",
    I | re.MULTILINE,
)
HEADING_DASH_RE = re.compile(
    r"^[ \t]*(?:[IVX]{1,4}\.|\d{1,2}[.)])?[ \t]*((?:Odwołując|Zamawiając)\w*)[ \t]*[–—][ \t]+", I | re.MULTILINE
)


TABLE_HEADING_RE = re.compile(r"^\s*(?:Odwołując|Zamawiając)\w*\s*$", I)
TABLE_LABELS = {
    "nazwa": "Nazwa",
    "adres": "Adres",
    "krs": "KRS",
    "nip": "NIP",
    "regon": "REGON",
    "rola w postępowaniu": "Rola",
    "rola": "Rola",
    "pełnomocnik": "Pełnomocnik",
    "kancelaria": "Kancelaria",
    "e-mail pełnomocnika": "e-mail",
    "e-mail": "e-mail",
}


def unfold_tables(text: str) -> str:
    """Give each value of a party table its label: "Nazwa", "KRS", ... in lines and then the values in lines."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        out.append(lines[i])
        if not TABLE_HEADING_RE.match(lines[i]):
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].strip().lower() in TABLE_LABELS:
            j += 1
        labels = [TABLE_LABELS[x.strip().lower()] for x in lines[i + 1 : j]]
        values = lines[j : j + len(labels)]
        if len(labels) < 3 or len(values) < len(labels):
            i += 1
            continue
        out[-1] = out[-1].strip() + ":"
        for label, value in zip(labels, values):
            if value.strip() not in ("", "-", "—", "–"):
                out.append(f"{label}: {value.strip()}")
        i = j + len(labels)
    return "\n".join(out)


def mark_headings(text: str) -> str:
    """Give each heading of a party a colon, because the text is flat after this step."""
    text = HEADING_LINE_RE.sub(r"\1:", text)
    return HEADING_DASH_RE.sub(r"\1: ", text)


ACTION_START_RE = re.compile(
    r"polegając\w*\s+na\s*:|polegają\s+na\s*:|wnoszę\s+o\s*:|Stan\s+faktyczny|\bZarzuty?\b"
    r"|zarzuc\w*\s+Zamawiającemu|Zaskarżon\w+\s+czynnoś\w+|następując\w+\s+czynności|\bUzasadnienie\b",
    I,
)


def _head(text: str) -> str:
    """Give the part of the text before the first charge."""
    m = ACTION_START_RE.search(text)
    return text[: m.start()] if m else text[:4000]


# --- sections of the header ------------------------------------------------------

ROLE_TAG_RE = re.compile(
    r"\(\s*(?:zamawiając|lider|partner|uczestni|prowadząc|odwołując|wykonawc|pełnomocnik|koordynator|wiodąc)[^()]{0,80}\)"
    r"|\s[–—-]\s(?:lider|partner)\w*(?:\s+zamawiając\w*)?(?:\s*,?\s*prowadząc\w+\s+postępowani\w+)?"
    r"|\s[–—-]\s(?:zamawiając\w*\s+)?(?:prowadząc|wiodąc)\w*(?:\s+postępowani\w*)?"
    r"|\s[–—-]\s(?:pełnomocnik\w*\s+zamawiając\w*)(?:\s+prowadząc\w*\s+postępowani\w*)?"
    r"|\s[–—-]\s(?:upoważnion\w*|prowadząc\w*)\s+(?:do\s+)?\w*\s*postępowani\w*"
    r"|\bRola\s*:\s*.*?(?=\s(?:NIP|KRS|REGON|Adres)\s*:|$)",
    I,
)
NAME_LABEL_RE = re.compile(r"\b(?:Adres(?:\s+siedziby)?|Siedziba)\s*:\s*$", I)
# A list number or a joining word before the name of a party: "1.", "2)", "a)", "•", "oraz".
LIST_MARK_RE = re.compile(r"^\s*(?:(?:\d{1,2}[.)]|[a-h]\)|[•·])\s*|oraz\s+|i\s+(?=[A-ZŁŚŻŹĆ]))+")
LEAD_WORD_RE = re.compile(
    r"\b(?:lider\w*|prowadząc\w+|wiodąc\w*|koordynator\w*|pełnomocnik\w*\s+zamawiając\w*|upoważnion\w*)\b", I
)


LEAD_SENTENCE_RE = re.compile(r"\bpostępowanie\s+prowadzi\s*:?\s*(.{5,120})", I)


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
        if mark.group("odw") or mark.group("odw2") or mark.group("odw3"):
            kind = "odwolujacy"
        elif mark.group("zam") or mark.group("zam2"):
            kind = "zamawiajacy"
        elif mark.group("odw4"):
            kind = "zamawiajacy" if mark.group("odw4").lower().startswith("zam") else "odwolujacy"
        elif mark.group("wyb"):
            kind = "wybrany"
        else:
            kind = "inny"
        end = marks[i + 1].start() if i + 1 < len(marks) else len(head)
        sections.append((kind, head[mark.start() : end]))
    return sections, procurement


def split_entities(section: str) -> list[dict]:
    """Find the entities of a section. An entity is a name, an address and identifiers.

    The role of an entity is the label before the name and the role words up to the next name.
    """
    anchors = [(m.start(), m.end(), m.group(0)) for m in IDS_RE.finditer(section)]
    if not anchors:
        m = STREET_RE.search(section)
        anchors = [(len(section), len(section), "")] if m else []
    entities, start = [], 0
    for a_start, a_end, ids in anchors:
        segment = section[start:a_start]
        seg_start, start = start, a_end
        m = STREET_RE.search(segment)
        if m:
            raw = segment[: m.start()]
        else:
            postal = POSTAL_RE.search(segment)
            named = re.search(r"Nazwa\s*:\s*(.+)$", segment, I)
            if postal:
                raw = segment[: postal.start()].rsplit(",", 1)[0]
            elif named:
                raw = "Nazwa: " + named.group(1)
            else:
                continue
        mails = list(EMAIL_TOKEN_RE.finditer(raw))
        if mails:
            raw = raw[mails[-1].end() :]
        # A number "2)" starts the next entity. A role line before it ("- prowadzący postępowanie")
        # belongs to the entity above, so it is not a part of this name.
        numbered = list(re.finditer(r"(?:^|\s)\d+\)\s*", raw))
        if numbered and ":" not in raw[numbered[-1].end() :]:
            raw = raw[numbered[-1].end() :]
        # A role before a colon ("1) Zamawiający – Lider:") belongs to this entity.
        label_role = " ".join(t.group(0) for t in ROLE_TAG_RE.finditer(raw.rpartition(":")[0]))
        raw = ROLE_TAG_RE.sub(" ", raw)
        raw = NAME_LABEL_RE.sub("", raw.rstrip())
        lead, _, name = raw.rpartition(":") if ":" in raw else ("", "", raw)
        marker = list(re.finditer(r"\d+\)", lead))
        role = (lead[marker[-1].end() :] if marker else lead) + " " + label_role
        name = LIST_MARK_RE.sub("", name.lstrip(" ,;.–-)"))
        name = re.sub(r"^(?:Działając\s+)?w\s+imieniu\s+(?:wykonawcy\s+)?", "", name.strip(), flags=I)
        name = name.strip(" ,;-")
        # A sole trader: "Jan Nowak prowadzący działalność gospodarczą pod firmą NOWAK-BUD Jan Nowak".
        firm = re.search(r"\bpod\s+(?:firmą|nazwą)\s*:?\s*(.+)$", name, I)
        if firm:
            name = firm.group(1).strip(' ,;-„”"')
        if name:
            pos = section.find(name[:20], seg_start)
            entities.append({"name": common.normalize_spaces(name), "ids": ids, "role": role, "pos": pos})
    tags = [(t.start(), t.group(0)) for t in ROLE_TAG_RE.finditer(section)]
    for i, e in enumerate(entities):
        end = entities[i + 1]["pos"] if i + 1 < len(entities) else len(section) + 1
        e["role"] += " " + " ".join(t for p, t in tags if e["pos"] <= p < end)
    return entities


def unique(entities: list[dict]) -> list[dict]:
    seen, out = set(), []
    for e in entities:
        key = re.sub(r"\W", "", e["name"].lower())
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


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


TITLE = r"(?:adw\.|r\.\s*pr\.|radc\w*\s+prawn\w+|adwokat\w*|mec\.|apl\.\s*(?:radc\.|adw\.)?)"
TITLES_RE = re.compile(rf"(?:{TITLE}\s+)+", I)
ANCHOR_RE = re.compile(
    r"(?P<rep>reprezentowan\w*\s+przez(?:\s+(?:swo\w+\s+)?pełnomocnik\w*\s*:?)?)|działa\w*\s+(?:przez|jako)\s+(?:ustanowion\w+\s+)?pełnomocnik\w*"
    r"|(?<!bez )pełnomocnik\w*(?:\s+(?:wykonawcy|Odwołującego))?",
    I,
)
NAME_WORD = r"[A-ZŁŚŻŹĆ][a-ząćęłńóśźż\-]+"
# A word before a colon is the label of the next line: "Jan Nowak Kontakt: ...".
PERSON_RE = re.compile(rf"{NAME_WORD}(?:\s+(?!Kancelari|Biuro|Adres|Spółk){NAME_WORD}(?![\w\-])(?!\s*:)){{1,2}}")
FIRM_AFTER_NAME_RE = re.compile(
    r"\s*(?:[–—-]|,|\(|\bz\b)\s*([^,()@]+?)\s*(?:,|\(|\)|$|\s+e-?mail\b|\s+tel\b|\s+adres\b|\s+\S+@)", I
)
# Words after a name that start the name of a law firm: "r. pr. Anna Nowak Nowak i Partnerzy Kancelaria ...".
FIRM_START_RE = re.compile(r"\s+(?:i|&)\s|\s+(?:Kancelari|Partner|Legal|Wspólni|sp\.|Spółk)", I)


def find_person(after: str) -> tuple[str, int] | None:
    """Give the name that stands after an anchor, without titles, and the end of the name."""
    m = re.match(r"\s*(?:wykonawcy|Odwołującego)?\s*[:–—-]*\s*(?:Imię\s+i\s+nazwisko\s*:)?\s*", after, I)
    pos = m.end() if m else 0
    t = TITLES_RE.match(after, pos)
    pos = t.end() if t else pos
    person = PERSON_RE.match(after, pos)
    if not person:
        return None
    words = person.group(0).split()
    # The surnames of the partners can stand before the firm word: "Szymański Dąbrowski Kancelaria".
    partners = re.compile(rf"(?-i:(?:\s+{NAME_WORD}){{0,2}})(?:{FIRM_START_RE.pattern})", I)
    if len(words) == 3 and partners.match(after, person.end()):
        # The flat text joins the name and the next line: the third word is the start of the firm.
        end = pos + person.group(0).rindex(words[2])
        return " ".join(words[:2]), end - 1
    return person.group(0), person.end()


def find_firm(region: str, name_end: int) -> str | None:
    m = re.search(r"adres\s+do\s+korespondencji\s*:\s*(.*?)(?=\s+tel\b|\s+e-?mail\b|\S+@|$)", region, I)
    if m:
        cut = ADDRESS_CUT_RE.search(m.group(1))
        firm = (m.group(1)[: cut.start()] if cut else m.group(1)).strip(" ,;")
        if firm and not STREET_RE.match(firm):  # only an address, without a name
            return firm
    m = FIRM_AFTER_NAME_RE.match(region, name_end)
    if m:
        cand = m.group(1).strip()
        if (
            len(cand.split()) >= 2
            and cand[0].isupper()
            and not re.match(rf"{TITLE}|ul\.|al\.|e-?mail|tel|ustanow", cand, I)
        ):
            # The flat text joins the firm and the address of the next line.
            street = STREET_RE.search(cand)
            return cand[: street.start()].strip() if street else cand
    m = re.search(
        rf"(?<![@.\w])(?-i:Kancelari)\w+(?!\s*:)\b.*?(?=\s*(?:,|\(|;)|\s+e-?mail\b|\s+tel\b|\s+adres\b|\s+[\w.\-]+@|\s+{STREET}|$)",
        region,
        I,
    )
    if m:
        # The surnames of the partners can stand before the word: "Nowak Kowalski Kancelaria Prawna sp.p.".
        gap = region[name_end : m.start()] if name_end <= m.start() else region[: m.start()]
        before = re.search(rf"(?:(?<=[\s,])|^)((?:(?:{NAME_WORD}|i|&)\s+){{1,4}})$", gap)
        names = before.group(1) if before and not TITLES_RE.search(before.group(1)) else ""
        # "r. pr. Anna Nowak, adw. Jan Kos Kancelaria ...": the names after a title are a second attorney.
        if before and re.search(rf"{TITLE}\s*$", gap[: before.start(1)], I):
            names = ""
        names = "" if re.search(r"\b(?:Pełnomocnik|Odwołując|Wykonawc)", names, I) else names
        # "z Kancelarii Radcy Prawnego ..." gives the name in the nominative: "Kancelaria Radcy Prawnego ...".
        return (names + m.group(0)).strip(" ,;")
    return None


def parse_attorney(
    section: str, evidence: dict[str, str], board_roles: list[str] = ()
) -> tuple[dict, str] | tuple[None, None]:
    """Give the attorney and the text that shows him, found with a role word or with a title."""
    roles = "|".join(board_roles) or "(?!)"
    board = re.compile(rf"\s*:?\s*(?:{roles})\b", I)
    board_after = re.compile(rf"\s*(?:[,–—-]|\()\s*(?:{roles})\b", I)
    found = None
    for m in ANCHOR_RE.finditer(section):
        person = find_person(section[m.end() :])
        # "reprezentowana przez Prezesa Zarządu" names a member of the board, not an attorney.
        is_board = board.match(section, m.end()) or (person and board_after.match(section[m.end() :], person[1]))
        if m.group("rep") and "pełnomocnik" not in m.group(0).lower() and is_board:
            continue
        if person or m.group("rep"):
            found = (m, person)
            break
    if found is None:
        for t in TITLES_RE.finditer(section):
            if re.search(r"Kancelari\w+[^,;]{0,40}$", section[max(t.start() - 60, 0) : t.start()], I):
                continue
            person = find_person(section[t.start() :])
            if person:
                found = (t, person)
                break
    if found is None:
        return None, None
    m, person = found
    pn = {"imie_nazwisko": None, "nazwa": None, "mail": None}
    after = section[m.end() :]
    if person:
        pn["imie_nazwisko"] = common.to_nominative(person[0])
        evidence["Odwolujacy[0].pelnomocnik.imie_nazwisko"] = person[0]
    # The text of the attorney ends where the next attorney or the text of the next section starts.
    firm = find_firm(after, person[1] if person else 0)
    if firm:
        # "z Kancelarii Radcy Prawnego ..." gives the name in the nominative: "Kancelaria Radcy Prawnego ...".
        firm = re.sub(r"^(?-i:Kancelari)(?:i|ą|ę)\b", "Kancelaria", firm)
        pn["nazwa"] = firm
        evidence["Odwolujacy[0].pelnomocnik.nazwa"] = firm
    mail = common.EMAIL_RE.search(after)
    if mail:
        pn["mail"] = mail.group(0).rstrip(".")
        label = re.search(r"e-?mail\s*:?\s*$", after[: mail.start()], I)
        evidence["Odwolujacy[0].pelnomocnik.mail"] = common.normalize_spaces(
            after[label.start() : mail.end()] if label else mail.group(0)
        )
    return pn, m.group(0)


LETTERHEAD_FIRM_RE = re.compile(rf"(?<![@.\w])(?-i:Kancelari)\w+\b.*?(?=\s*[,;(]|\s+{STREET}|\s+\d{{2}}-\d{{3}}|\s+tel\b|\s+e-?mail\b|$)", I)


def letterhead_of_firm(top: str, attorney: dict, evidence: dict[str, str]) -> None:
    """The law firm can write the appeal on its letterhead, above the town and the date."""
    m = LETTERHEAD_FIRM_RE.search(top)
    if not m:
        return
    attorney["nazwa"] = evidence["Odwolujacy[0].pelnomocnik.nazwa"] = m.group(0).strip()
    mail = common.EMAIL_RE.search(top, m.end())
    if mail and not attorney["mail"]:
        attorney["mail"] = mail.group(0).rstrip(".")
        evidence["Odwolujacy[0].pelnomocnik.mail"] = mail.group(0)


# --- the header line with the town and the date -----------------------------------


def find_place_and_date(head: str) -> tuple[str | None, str | None, str | None]:
    """Find a line like "Gdańsk, dnia 3 września 2026 roku" or "Gdańsk 03.09.2026"."""
    for m in PLACE_DATE_RE.finditer(head):
        iso = common.parse_date(re.fullmatch(common.DATE_RE, m.group("date")))
        if not iso:
            continue
        words = m.group("city").split()
        # The title of the letter can stand before the town in the flat text: "Odwołanie Warszawa, 29 marca 2026".
        while len(words) > 1 and re.fullmatch(r"Odwołani\w*|Pismo|ODWOŁANIE", words[0]):
            words = words[1:]
        # After a postal code, the first word is the town of an address.
        if len(words) > 1 and re.search(r"\d{2}-\d{3}\s*$", head[: m.start("city")]):
            words = words[1:]
        return " ".join(words), iso, m.group(0)
    return None, None, None


# --- the contested action ----------------------------------------------------------


LISTED_ACTION_RE = re.compile(r"wnoszę\s+odwołanie\s+(?:wobec|od)\s*:?\s*1\s*[.)]\s*(.*?)(?=;|\s2\s*[.)]\s)", I)


def listed_first_action(text: str) -> str | None:
    """A usual form: "wnoszę odwołanie wobec: 1. czynności ...; 2. ...". The first item is the first action."""
    m = LISTED_ACTION_RE.search(text)
    return common.normalize_spaces(m.group(1)) if m else None


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
    """Give the code and the words of the text that match a rule, with some text around them.

    In one text the match that starts first wins. For the same start, the first rule wins.
    A rule with "fallback" counts only if no other rule matches.
    """
    for text in texts:
        for fallback in (False, True):
            best = None
            for index, rule in enumerate(rules):
                if bool(rule.get("fallback")) != fallback:
                    continue
                for pattern in rule["patterns"]:
                    m = re.search(pattern, text, I)
                    if m and (best is None or (m.start(), index) < best[0]):
                        best = ((m.start(), index), int(rule["code"]), m)
            if best:
                m = best[2]
                return best[1], text[max(m.start() - 60, 0) : m.end() + 60]
    return None, ""


ITEM_RE = re.compile(r"(?:(?<=\s)|^)(?:\d{1,2}[.)]|[IVX]{1,4}\.|§\s*\d+|Zarzut(?:\s+nr)?\s*\d+\s*[.:–-]?)(?=\s)")
SENTENCE_RE = re.compile(
    r"(?<=[.;!?])(?<!\bart\.)(?<!\bust\.)(?<!\bpkt\.)(?<!\bnr\.)(?<!\bul\.)(?<!\bal\.)(?<!\bpr\.)(?<!\badw\.)\s+(?=[A-ZŁŚŻŹĆ„\"])"
)


def date_in(text: str) -> tuple[str | None, str]:
    """Give the date of an action. A date after "w dniu" or "dnia" is better than another date."""
    for m in re.finditer(r"(?:w\s+dniu|dnia)\s+", text, I):
        dates = common.find_dates(text[m.end() : m.end() + 40])
        if dates and dates[0][0] <= 1:
            return dates[0][1], text[m.start() : m.end() + 30]
    dates = common.find_dates(text)
    return (dates[0][1], text[max(dates[0][0] - 30, 0) : dates[0][0] + 20]) if dates else (None, "")


def action_date(texts: list[str]) -> tuple[str | None, str]:
    for text in texts:
        day, source = date_in(text)
        if day:
            return day, source
    return None, ""


def locate_first_charge(text: str, rules: list[dict]) -> tuple[int | None, str, str | None, str]:
    """Find the first charge: the first sentence after the start of the charges that names an action."""
    m = ACTION_START_RE.search(text)
    body = text[m.end() :] if m else text
    marks = [x.start() for x in ITEM_RE.finditer(body)]
    bounds = sorted({0, *marks, len(body)})
    for a, b in itertools.pairwise(bounds):
        item = body[a:b]
        offset = 0
        for sentence in SENTENCE_RE.split(item):
            rest = item[offset:]
            offset += len(sentence) + 1
            code, source = classify_action([sentence], rules)
            if code:
                day, day_source = date_in(sentence)
                if not day:
                    day, day_source = date_in(rest)
                return code, source, day, day_source
    return None, "", None, ""


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
    if ted is None:
        # A number of the TED form without a label, for example "ogłoszenie 2026/BZP 00842365, 961192-2026".
        m = re.search(r"(?<![\d/.\-])(\d{6})\s*-\s*(20\d\d)(?![\d/.\-])", block)
        ted = f"{m.group(1)}-{m.group(2)}" if m else None
    out["numer_ted"] = ted
    sources["numer_ted"] = m.group(0) if m else ""
    m = re.search(r"(?:nr|numer|znak)\s+(?:referencyjny|sprawy|postępowania)(?:\s+sprawy)?\s*:?\s*([^\s,;]+)", block, I)
    if not m:
        m = re.search(r"Postępowanie\s+nr\s+([^\s,;:]+)", block) or re.search(
            r"[”\"»]\s*\(([^()\s]*\d[^()\s]*)\)", block
        )
    if not m:
        for cand in re.finditer(r"\b(?:nr|numer)\s+([^\s,;:]*\d[^\s,;:]*)", block, I):
            if not re.search(r"BZP|^\d{6}-\d{4}$|^\d{4}/S$", cand.group(1)):
                m = cand
                break
    if not m:
        m = re.search(r"\(\s*([A-Z0-9.]*[A-Z]*[./][A-Z0-9./]*\d[A-Z0-9./]*)\s*\)", block)
    out["numer_postepowania"] = m.group(1).rstrip(".") if m else None
    sources["numer_postepowania"] = m.group(0) if m else ""
    quotes = '„"“«'
    closing = '”"»'
    # The OCR can lose the first quote mark, so it is optional.
    m = re.search(rf"pn\.?\s*[{quotes}]?(.+?)[{closing}]['’]?\s*(?:,|\.|$|(?:nr|numer|znak)\b)", block)
    if m:
        out["tytul"], sources["tytul"] = m.group(1).strip(), m.group(0).rstrip(" ,.")
    else:
        label = (
            r"(?:Przedmiot\s+(?:zamówienia|odwołani\w*)|Tytuł(?:\s+postępowania)?|Nazwa\s+(?:postępowania|zamówienia)"
            r"|(?-i:Postępowanie)(?:\s+nr\s+[^\s:]+)?)\s*:\s*"
        )
        # The OCR can lose the first quote. A colon means that the text after the label is not a quoted title.
        m = re.search(label + rf"[{quotes}]?([^{quotes}{closing}:]{{4,200}}?)[{closing}]", block, I)
        if m:
            out["tytul"], sources["tytul"] = m.group(1).strip(), m.group(0).rstrip(" ,.")
            for key, value in out.items():
                if value:
                    evidence[f"ZamowieniePubliczne.{key}"] = sources[key]
            return out
        m = re.search(
            r"(?:Przedmiot\s+(?:zamówienia|odwołani\w*)|Tytuł(?:\s+postępowania)?|Nazwa\s+(?:postępowania|zamówienia)"
            r"|(?-i:Postępowanie)(?:\s+nr\s+[^\s:]+)?)\s*:\s*(.+?)(?=\s*[.,;]?\s+(?:Numer|Znak|Nr|BZP|TED|Ogłoszenie|ogłoszenie|Zaskarżon|Dane|Wartość)\b"
            r"|\s*\(\s*[^()\s]*\d|\s*$)",
            block,
            I,
        )
        title = m.group(1).strip(" .,;").rstrip(closing) if m else None
        quoted = re.match(rf"[{quotes}](.+?)[{closing}]", title) if title else None
        if not title:
            m = re.search(rf"(?-i:Postępowanie)\s+[{quotes}]?((?-i:[A-ZŁŚŻŹĆ])[^{closing}]{{4,250}}?)[{closing}]", block)
            m = m or re.search(rf"[{quotes}](.+?)[{closing}]", block)
            title = m.group(1).strip() if m else None
        out["tytul"] = quoted.group(1).strip() if quoted else title
        sources["tytul"] = m.group(0).rstrip(" ,.") if m else ""
    for key, value in out.items():
        if value:
            evidence[f"ZamowieniePubliczne.{key}"] = sources[key]
    return out


def extract(text: str, doc_type: DocType, evidence: dict[str, str]) -> dict:
    data = doc_type.empty()
    text = common.despace_caps(text)
    text = PAGE_LINE_RE.sub("", text)
    text = flat(mark_headings(unfold_tables(text)))
    head = _head(text)
    sections, procurement = split_head(head)
    if not any(k == "odwolujacy" for k, _ in sections):
        # Without the word "Odwołujący", the contractor that brings the appeal has the heading "Wykonawca:".
        alt = re.sub(r"(?<![\w(])Wykonawc[aya]\s*:", "Odwołujący:", head, count=1, flags=I)
        if alt != head:
            sections, procurement = split_head(alt)

    kio = data["OdwolanieKIO"]
    place, day, line = find_place_and_date(head)
    if day:
        kio["data"], kio["miejscowosc"] = day, place
        evidence["OdwolanieKIO.data"] = evidence["OdwolanieKIO.miejscowosc"] = line

    rules = doc_type.raw.get("action_rules", [])
    code, source, action_day, day_source = None, "", None, ""
    listed = listed_first_action(text)
    if listed:
        code, source = classify_action([listed], rules)
        action_day, day_source = action_date([listed])
    if not code:
        code, source, action_day, day_source = locate_first_charge(text, rules)
    if not code:
        texts = first_charge_texts(text)
        code, source = classify_action(texts, rules)
        action_day, day_source = action_date(texts)
    if code:
        kio["czynnosc_powod_id"] = code
        kio["czynnosc_opis"] = str(doc_type.raw["actions"][code])
        evidence["OdwolanieKIO.czynnosc_powod_id"] = evidence["OdwolanieKIO.czynnosc_opis"] = source
    kio["czynnosc_dzien"] = action_day
    if action_day:
        evidence["OdwolanieKIO.czynnosc_dzien"] = day_source

    appellant_sections = [s for k, s in sections if k == "odwolujacy"]
    appellants = unique([e for s in appellant_sections for e in split_entities(s)])
    if appellants:
        leader = next((a for a in appellants if "lider" in a["role"].lower()), appellants[0])
        row = entity_fields(leader, "Odwolujacy[0]", evidence)
        board_roles = doc_type.raw.get("board_roles", [])
        attorney, attorney_text = parse_attorney(" ".join(appellant_sections), evidence, board_roles)
        if attorney is None:
            # The block of the attorney can stand before the appellant: "Pełnomocnik Odwołującego: ...".
            other = [
                s for k, s in sections if k == "inny" and re.match(r"\s*Pełnomocnik\w*\s+(?:Odwołując|wykonawc)", s, I)
            ]
            other += [
                m.group(0) for m in re.finditer(r"Pełnomocnik\w*\s+Odwołując\w*\s*:.{0,300}", head, I | re.DOTALL)
            ]
            for block in other:
                attorney, attorney_text = parse_attorney(block, evidence, board_roles)
                if attorney:
                    break
        if attorney is None:
            # Only an attorney signs with a professional title: "adw. Jan Nowak" under the appeal.
            signature = text[-700:]
            title = TITLES_RE.search(signature)
            person = find_person(signature[title.start() :]) if title else None
            if person:
                attorney = {"imie_nazwisko": common.to_nominative(person[0]), "nazwa": None, "mail": None}
                attorney_text = common.normalize_spaces(signature[title.start() : title.start() + person[1]])
                evidence["Odwolujacy[0].pelnomocnik.imie_nazwisko"] = attorney_text
        if attorney and not attorney["nazwa"] and line:
            letterhead_of_firm(head[: head.find(line)][-400:], attorney, evidence)
        row["przez-pelnomocnika"] = 1 if attorney else 0
        row["pelnomocnik"] = attorney
        # Without an attorney the decision comes from the start of the section of the appellant.
        evidence["Odwolujacy[0].przez-pelnomocnika"] = attorney_text or appellant_sections[0][:100].strip()
        data["Odwolujacy"] = [row]

    authorities = unique([e for k, s in sections if k == "zamawiajacy" for e in split_entities(s)])
    many = len(authorities) > 1
    lead_sentence = LEAD_SENTENCE_RE.search(head)
    for entity in authorities if many and lead_sentence else ():
        if entity["name"][:15].lower() in lead_sentence.group(1).lower():
            entity["role"] += " prowadzący"
    for i, entity in enumerate(authorities):
        row = entity_fields(entity, f"Zamawiajacy[{i}]", evidence)
        row["prowadzacy_postepowanie"] = None
        if many:
            lead = LEAD_WORD_RE.search(entity["role"])
            row["prowadzacy_postepowanie"] = 1 if lead else 0
            # The role joins texts from several places, so the evidence is the keyword or the name.
            evidence[f"Zamawiajacy[{i}].prowadzacy_postepowanie"] = lead.group(0) if lead else entity["name"]
        data["Zamawiajacy"].append(row)

    # The names of the parties can have quotes, so the text of the procurement is the head without them.
    residual = head
    for entity in appellants + authorities:
        residual = residual.replace(entity["name"], " ")
    data["ZamowieniePubliczne"].update(parse_procurement(procurement or residual, evidence))
    return data
