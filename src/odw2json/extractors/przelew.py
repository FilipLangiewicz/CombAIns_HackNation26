"""The extractor for the type "przelew" (the confirmation of a bank transfer).

The label aliases are in the key "labels" of config/types/przelew.yaml.
"""

from __future__ import annotations

import re

from odw2json import common
from odw2json.classify import DocType

LEADER = re.compile(r"\s*\.{3,}\s*")
PRINT_LINE = re.compile(r"wydruk|wygenerowan|sporządzon|^\s*\w+,\s+\d", re.IGNORECASE)
ACCOUNT = re.compile(r"(?<![\w])(?:PL\s*)?(?:\d{2}(?:\s?\d{4}){6}|\d{26})(?!\d)")
OPEN_QUOTES, CLOSE_QUOTES = "„\"«", "”\"»"


def prepare_lines(text: str) -> list[str]:
    """Split the text into lines. A row of dots between a label and a value becomes a colon."""
    lines = []
    for line in text.splitlines():
        line = common.normalize_spaces(LEADER.sub(": ", line)).strip(": ")
        if line and not re.fullmatch(r"[-=_*\s]+|\*+ .* \*+", line):
            lines.append(line)
    return lines


def find_label(lines: list[str], patterns: list[str], start: int = 0) -> tuple[int, re.Match] | None:
    for pattern in patterns:
        for i in range(start, len(lines)):
            m = re.search(pattern, lines[i], re.IGNORECASE)
            if m:
                return i, m
    return None


def value_texts(lines: list[str], i: int, m: re.Match) -> list[str]:
    """Give the text after the label on the same line, then the next line."""
    rest = lines[i][m.end() :].lstrip(" :-")
    nxt = lines[i + 1] if i + 1 < len(lines) else ""
    return [t for t in (rest, nxt) if t]


def find_by_label(lines: list[str], patterns: list[str], parse) -> tuple[object, str] | None:
    """Parse the value that follows the first label that gives a value."""
    for pattern in patterns:
        for i, line in enumerate(lines):
            m = re.search(pattern, line, re.IGNORECASE)
            if not m:
                continue
            for k, part in enumerate(value_texts(lines, i, m)):
                value = parse(part)
                if value is not None:
                    return value, " ".join(lines[i : i + 1 + (k and 1)])
    return None


def parse_amount(part: str) -> float | None:
    # A bare number without a decimal part or a currency is not an amount (for example a date).
    if not re.search(r"\d[,.]\d{1,2}(?!\d)|PLN|zł", part):
        return None
    return common.parse_amount(re.sub(r"(?<=\d)\s*(?:PLN|zł)", "", part))


def parse_reference(part: str) -> str | None:
    m = re.match(r"[A-Z0-9][\w/\-]{4,}", part.strip(), re.IGNORECASE)
    return m.group(0) if m and re.search(r"\d", m.group(0)) else None


def find_title(lines: list[str], labels: dict) -> tuple[str, str] | None:
    found = find_label(lines, labels["tytul"])
    if not found:
        return None
    i, m = found
    stop = re.compile("|".join(labels["stop"]), re.IGNORECASE)
    first = lines[i][m.end() :].lstrip(" :-")
    parts = [first] if first else []
    quoted = bool(first) and first[0] in OPEN_QUOTES
    for line in lines[i + 1 :]:
        if parts and not quoted and stop.search(line):
            break
        parts.append(line)
        if quoted and line[-2:].strip(".").endswith(tuple(CLOSE_QUOTES)):
            break
    title = " ".join(parts).strip()
    if quoted:
        title = title.lstrip(OPEN_QUOTES).split("”")[0].rstrip(".").rstrip(CLOSE_QUOTES)
    return (title.strip(), lines[i]) if title.strip() else None


def find_accounts(text: str, labels: dict) -> dict[str, str]:
    """Give the account of the sender and of the recipient by the nearest keyword before each account."""
    flat = " ".join(text.split())
    patterns = {role: re.compile(labels[role][0], re.IGNORECASE) for role in ("z_rachunku", "na_rachunek")}
    result: dict[str, str] = {}
    free = []
    for m in ACCOUNT.finditer(flat):
        number = common.digits(m.group(0))[-26:]
        context = flat[max(0, m.start() - 250) : m.start()]
        nearest = {
            role: max((k.end() for k in pattern.finditer(context)), default=-1) for role, pattern in patterns.items()
        }
        role = max(nearest, key=nearest.get) if max(nearest.values()) >= 0 else None
        if role and role not in result:
            result[role] = number
        else:
            free.append(number)
    for role in ("z_rachunku", "na_rachunek"):
        if role not in result and free:
            result[role] = free.pop(0)
    return result


def find_date(lines: list[str], labels: dict) -> tuple[str, str] | None:
    found = find_by_label(lines, labels["data_operacji"], common.first_date)
    if found:
        return found
    for line in lines:
        iso = common.first_date(line)
        if iso and not PRINT_LINE.search(line):
            return iso, line
    return None


def extract(text: str, doc_type: DocType, evidence: dict[str, str]) -> dict:
    data = doc_type.empty()
    box = data["przelew_bankowy"]
    labels = doc_type.raw.get("labels", {})
    lines = prepare_lines(text)

    def put(name: str, found) -> None:
        if found:
            box[name], evidence[f"przelew_bankowy.{name}"] = found

    put("data_operacji", find_date(lines, labels))
    put("kwota", find_by_label(lines, labels["kwota"], parse_amount))
    reference = find_by_label(lines, labels["numer_transakcji"], parse_reference)
    if not reference:
        m = re.search(doc_type.raw.get("fallback", {}).get("numer_transakcji", r"(?!)"), text)
        reference = (m.group(0), m.group(0)) if m else None
    put("numer_transakcji", reference)
    put("tytul", find_title(lines, labels))
    for role, number in find_accounts(text, labels).items():
        box[role] = number
        evidence[f"przelew_bankowy.{role}"] = number
    return data
