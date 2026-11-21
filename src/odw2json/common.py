"""Shared functions for all extractors: identifiers, dates, amounts, accounts and names."""

from __future__ import annotations

import functools
import re
from datetime import date
from pathlib import Path

import yaml

MONTHS = {
    "stycznia": 1, "styczeń": 1, "styczen": 1, "lutego": 2, "luty": 2, "marca": 3, "marzec": 3,
    "kwietnia": 4, "kwiecień": 4, "maja": 5, "maj": 5, "czerwca": 6, "czerwiec": 6,
    "lipca": 7, "lipiec": 7, "sierpnia": 8, "sierpień": 8, "września": 9, "wrzesień": 9,
    "października": 10, "październik": 10, "listopada": 11, "listopad": 11, "grudnia": 12, "grudzień": 12,
}  # fmt: skip
ROMAN = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
    "xi": 11,
    "xii": 12,
}

MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
DATE_RE = re.compile(
    rf"(?<!\d)(?:"
    rf"(?P<d1>\d{{1,2}})\s*[.\-/]\s*(?P<m1>\d{{1,2}})\s*[.\-/]\s*(?P<y1>\d{{4}})"
    rf"|(?P<y2>\d{{4}})\s*[.\-/]\s*(?P<m2>\d{{1,2}})\s*[.\-/]\s*(?P<d2>\d{{1,2}})"
    rf"|(?P<d3>\d{{1,2}})\s+(?P<m3>{MONTH_RE})\s+(?P<y3>\d{{4}})"
    rf"|(?P<d4>\d{{1,2}})\s+(?P<m4>[ivxIVX]{{1,4}})\s+(?P<y4>\d{{4}})"
    rf")(?!\d)",
    re.IGNORECASE,
)


def parse_date(match: re.Match) -> str | None:
    g = match.groupdict()
    try:
        if g["d1"]:
            d, m, y = int(g["d1"]), int(g["m1"]), int(g["y1"])
        elif g["y2"]:
            d, m, y = int(g["d2"]), int(g["m2"]), int(g["y2"])
        elif g["d3"]:
            d, m, y = int(g["d3"]), MONTHS[g["m3"].lower()], int(g["y3"])
        else:
            d, m, y = int(g["d4"]), ROMAN[g["m4"].lower()], int(g["y4"])
        return date(y, m, d).isoformat()
    except (ValueError, KeyError):
        return None


def find_dates(text: str) -> list[tuple[int, str]]:
    """Give (position, ISO date) for each date in the text."""
    found = []
    for m in DATE_RE.finditer(text):
        iso = parse_date(m)
        if iso:
            found.append((m.start(), iso))
    return found


def first_date(text: str) -> str | None:
    dates = find_dates(text)
    return dates[0][1] if dates else None


AMOUNT_RE = re.compile(r"(?<![\d,.])(\d{1,3}(?:[ . ']\d{3})+|\d+)(?:[,.](\d{1,2}))?(?![\d])")


def parse_amount(text: str) -> float | None:
    """Read the first amount, for example "10 000,00 PLN" or "1.234,50 zł"."""
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    whole = re.sub(r"[ . ']", "", m.group(1))
    frac = m.group(2) or "0"
    return float(f"{whole}.{frac}")


ACCOUNT_RE = re.compile(r"(?:PL\s*)?\d{2}(?:[ \-]?\d{4}){6}(?!\d)|(?:PL\s*)?\d{26}(?!\d)")


def find_accounts(text: str) -> list[tuple[int, str]]:
    """Give (position, 26 digits) for each Polish bank account. The JSON has no "PL" prefix."""
    return [(m.start(), re.sub(r"\D", "", m.group(0))) for m in ACCOUNT_RE.finditer(text)]


def digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def labelled(text: str, label: str, length: int | tuple[int, ...]) -> tuple[str, str] | None:
    """Find a number after a label, for example "NIP: 123-456-32-18". Give the digits and the source text."""
    lengths = (length,) if isinstance(length, int) else length
    pattern = re.compile(rf"\b{label}\b\s*(?:nr|numer)?\s*[:.\-]?\s*(?:PL)?\s*([\d][\d \-]{{6,22}}\d)", re.IGNORECASE)
    for m in pattern.finditer(text):
        value = digits(m.group(1))
        for n in sorted(lengths, reverse=True):
            if len(value) >= n:
                return value[:n], normalize_spaces(m.group(0))
    return None


def labelled_number(text: str, label: str, length: int | tuple[int, ...]) -> str | None:
    found = labelled(text, label, length)
    return found[0] if found else None


def find_nip(text: str) -> str | None:
    return labelled_number(text, "NIP", 10)


def find_krs(text: str) -> str | None:
    return labelled_number(text, "KRS", 10)


def find_regon(text: str) -> str | None:
    return labelled_number(text, "REGON", (14, 9))


def find_pesel(text: str) -> str | None:
    return labelled_number(text, "PESEL", 11)


EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")


def find_email(text: str) -> str | None:
    m = EMAIL_RE.search(text)
    return m.group(0).rstrip(".") if m else None


# --- names of persons ---------------------------------------------------------

PERSON_TITLES = re.compile(
    r"^(?:(?:r\.\s*pr\.|radca\s+prawny|radcy\s+prawnego|radcę\s+prawnego|adw\.|adwokat(?:a|owi)?|"
    r"apl\.\s*(?:radc\.|adw\.)|aplikant(?:a)?\s+\w+|mec\.|pan(?:a|i|ią|u)?|p\.|dr\.?|prof\.|hab\.|inż\.|mgr\.?)\s+)+",
    re.IGNORECASE,
)


def strip_titles(name: str) -> str:
    name = PERSON_TITLES.sub("", name.strip())
    name = re.sub(r",?\s*(?:r\.\s*pr\.|adw\.|radca prawny|adwokat)\s*$", "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", name).strip(" ,.;:")


NAMES_FILE = Path(__file__).resolve().parents[2] / "config" / "names.yaml"

# Surname endings of the adjective type: "Kowalskiego", "Kowalskim" (masculine), "Kowalskiej", "Kowalską" (feminine).
MASC_ADJECTIVE = re.compile(r"(?:iego|iemu|im)$")
UNAMBIGUOUS_MASC = re.compile(r"(?<=[scz]k)(?:iego|iemu|im)$")
UNAMBIGUOUS_FEM = re.compile(r"(?<=[scz]k)(?:iej|ą)$")
# A case suffix of a first name and the ending of the nominative.
MASC_SUFFIXES = (("iem", ""), ("owi", ""), ("em", ""), ("iego", "i"), ("ego", "y"), ("a", ""), ("u", ""))
FEM_SUFFIXES = (("ą", "a"), ("ę", "a"), ("y", "a"), ("i", "a"), ("dze", "ga"), ("dze", "da"), ("cie", "ta"),
                ("ce", "ka"), ("rze", "ra"), ("ie", "a"), ("ze", "za"))  # fmt: skip


@functools.cache
def first_names() -> tuple[frozenset[str], frozenset[str]]:
    """Read the male and the female first names from config/names.yaml."""
    cfg = yaml.safe_load(NAMES_FILE.read_text(encoding="utf-8"))
    return frozenset(cfg["first_names_masc"]), frozenset(cfg["first_names_fem"])


def _masc_first_name(token: str, names: frozenset[str]) -> str | None:
    for suffix, nominative in MASC_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            stem = token[: len(token) - len(suffix)]
            # A stem can lose a vowel in the oblique case: Marek -> Marka.
            for candidate in (stem + nominative, stem[:-1] + "e" + stem[-1] + nominative):
                if candidate in names:
                    return candidate
    return None


def _fem_first_name(token: str, names: frozenset[str]) -> str | None:
    for suffix, nominative in FEM_SUFFIXES:
        if token.endswith(suffix) and token[: len(token) - len(suffix)] + nominative in names:
            return token[: len(token) - len(suffix)] + nominative
    return None


def to_nominative(
    name: str, first_names_masc: frozenset[str] | None = None, first_names_fem: frozenset[str] | None = None
) -> str:
    """Change a name from another case to the nominative.

    The first name gives the gender. A name that is already nominative does not change.
    If the first name is unknown, only a surname with an unambiguous ending ("-skiego", "-ską") changes.
    """
    if first_names_masc is None or first_names_fem is None:
        first_names_masc, first_names_fem = first_names()
    parts = name.split()
    if len(parts) < 2:
        return name
    first, last = parts[0], parts[-1]
    oblique = False
    if first in first_names_masc or first in first_names_fem:
        masculine = first in first_names_masc
    elif _masc_first_name(first, first_names_masc):
        first, masculine, oblique = _masc_first_name(first, first_names_masc), True, True
    elif _fem_first_name(first, first_names_fem):
        first, masculine, oblique = _fem_first_name(first, first_names_fem), False, True
    else:
        last = UNAMBIGUOUS_MASC.sub("i", last)
        last = UNAMBIGUOUS_FEM.sub("a", last)
        return " ".join([first, *parts[1:-1], last])
    if masculine and MASC_ADJECTIVE.search(last):
        last = MASC_ADJECTIVE.sub("i", last)
    elif masculine and oblique:
        last = re.sub(r"(?:kiem|owi|em|a|u)$", lambda m: "k" if m.group(0) == "kiem" else "", last)
    elif not masculine:
        last = re.sub(r"(?:iej|ej|ą)$", "a", last)
    return " ".join([first, *parts[1:-1], last])


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def despace_caps(text: str) -> str:
    """Join titles with spaces between letters, for example "P E Ł N O M O C N I C T W O"."""
    return re.sub(r"\b(?:\w ){3,}\w\b", lambda m: m.group(0).replace(" ", ""), text)
