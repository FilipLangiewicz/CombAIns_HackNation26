"""The extractor for the type "przelew" (the confirmation of a bank transfer).

The label aliases are in the key "labels" of config/types/przelew.yaml.
"""

from __future__ import annotations

import difflib
import re

from odw2json import common
from odw2json.classify import DocType

LEADER = re.compile(r"\s*\.{3,}\s*")
PRINT_LINE = re.compile(r"wydruk|wygenerowan|sporządzon|^\s*\w+,\s+\d", re.IGNORECASE)
# A Polish account (26 digits, with or without "PL") or an IBAN of another country (two letters, two digits).
ACCOUNT = re.compile(
    r"(?<![\w])(?:(?:PL[\s-]*)?(?:\d{2}(?:[\s-]?\d{4}){6}|\d{26}|\d(?:[ .\-]?\d){25})(?![\d.]?\d)"
    r"|(?!PL)[A-Z]{2}\d{2}(?:[\s-]?[A-Z0-9]{4}){2,7}(?:[\s-]?[A-Z0-9]{1,3})?(?![\w]))"
)
# A fee or a balance is not the amount of the transfer.
NOT_AMOUNT = re.compile(r"saldo|balance|\bfee\b|commission|prowizj|opłat[aęy]\s+(?:za|bankow|przelew)", re.IGNORECASE)
CURRENCY = re.compile(r"\bPLN\b|(?<![\wąćęłńóśźż])zł(?![\wąćęłńóśźż])")
# A second label for the same field after a slash, for example "Tytuł / Title:".
ALTERNATIVE = re.compile(r"^/\s*[^:/\d]{1,40}:\s*")
PAGE_MARKER = re.compile(
    r"(?:strona|str\.?|page)\s*\d+(?:\s*(?:z|/|of)\s*\d+)?|[-–]\s*\d{1,3}\s*[-–]|\d{1,3}\s*/\s*\d{1,3}", re.IGNORECASE
)
OPEN_QUOTES, CLOSE_QUOTES = '„"«', '”"»'


def prepare_lines(text: str) -> list[str]:
    """Split the text into lines. A row of dots between a label and a value becomes a colon."""
    lines = []
    for line in text.splitlines():
        line = common.normalize_spaces(LEADER.sub(": ", line)).strip(": ")
        if line and not re.fullmatch(r"[-=_*\s]+|\*+ .* \*+", line) and not PAGE_MARKER.fullmatch(line):
            lines.append(line)
    return lines


def is_label_only(line: str, patterns: list[str]) -> bool:
    """A short line with a label and without a value."""
    text = line.rstrip(": ")
    if len(text.split()) > 5 or re.search(r"\d|:", text):
        return False
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def merge_columns(lines: list[str], patterns: list[str]) -> list[str]:
    """Join a table where all labels come first and then all values: label i gets value i."""
    result, i = [], 0
    while i < len(lines):
        k = 0
        while i + k < len(lines) and is_label_only(lines[i + k], patterns):
            k += 1
        values = lines[i + k : i + 2 * k]
        if k >= 2 and len(values) == k and not any(is_label_only(v, patterns) for v in values):
            result += [f"{lines[i + j].rstrip(': ')}: {values[j]}" for j in range(k)]
            i += 2 * k
        else:
            result += lines[i : i + max(k, 1)]
            i += max(k, 1)
    return result


def find_label(lines: list[str], patterns: list[str], start: int = 0) -> tuple[int, re.Match] | None:
    for pattern in patterns:
        for i in range(start, len(lines)):
            m = re.search(pattern, lines[i], re.IGNORECASE)
            if m:
                return i, m
    return None


def value_texts(lines: list[str], i: int, m: re.Match) -> list[str]:
    """Give the text after the label, the text joined with the next line, and the next line."""
    rest = ALTERNATIVE.sub("", lines[i][m.end() :].lstrip(" :-")).lstrip(" :-")
    nxt = lines[i + 1] if i + 1 < len(lines) else ""
    return [t for t in (rest, f"{rest} {nxt}" if rest else "", nxt) if t.strip()]


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
                    return value, " ".join(lines[i : i + 1 + bool(k)])
    return None


def parse_amount(part: str) -> float | None:
    # A bare number without a decimal part or a currency is not an amount (for example a date).
    if not re.search(r"\d[,.]\d{1,2}(?!\d)|PLN|zł", part):
        return None
    if re.fullmatch(r"\s*\d{1,4}[./-]\d{1,2}[./-]\d{1,4}\s*", part):
        return None  # a date, for example "11.09.2026" in the next line of a table
    return common.parse_amount(re.sub(r"(?<=\d)\s*(?:PLN|zł)", "", part))


def find_amount(lines: list[str], labels: dict) -> tuple[float, str] | None:
    """Use the label. Else use the first line with a currency, for example "- 7 500,00 PLN"."""
    lines = ["" if NOT_AMOUNT.search(line) else line for line in lines]
    found = find_by_label(lines, labels["kwota"], parse_amount)
    if found:
        return found
    for line in lines:
        if CURRENCY.search(line):
            value = parse_amount(ACCOUNT.sub("", line))
            if value is not None:
                return value, line
    return None


def parse_reference(part: str) -> str | None:
    m = re.match(r"[A-Z0-9][\w/\-]{4,}", part.strip(), re.IGNORECASE)
    return m.group(0) if m and re.search(r"\d", m.group(0)) else None


def cut_at_label(text: str, words: list[str], ambiguous: list[str]) -> str:
    """Cut the text before a label word with a capital letter. A PDF reader can join a title with the next line.

    A word such as "NR" can also be a part of the title. It is a label only when a number does not follow it.
    """
    for m in re.finditer(rf"\s(?=({'|'.join(words)})(?![\wąćęłńóśźż]))", text, re.IGNORECASE):
        word = m.group(1)
        if not word[0].isupper():
            continue
        if word.lower() in ambiguous and re.match(r"[\s.]*\d", text[m.end() + len(word) :]):
            continue
        return text[: m.start()]
    return text


def find_title(lines: list[str], labels: dict, reference: str | None) -> tuple[str, str] | None:
    found = find_label(lines, labels["tytul"])
    if not found:
        return None
    i, m = found
    stop = re.compile(rf"\s*(?:{'|'.join(labels['stop'])})(?![\wąćęłńóśźż])", re.IGNORECASE)
    first = lines[i][m.end() :].lstrip(" :-")
    parts = [first] if first else []
    quoted = bool(first) and first[0] in OPEN_QUOTES
    for line in lines[i + 1 :]:
        # The title of a bank transfer often ends with the reference number.
        if reference and parts and parts[-1].endswith(reference) and not quoted:
            break
        if parts and not quoted and line[0].isupper() and stop.match(line):
            break
        parts.append(line)
        if quoted and any(q in line for q in CLOSE_QUOTES):
            break
    title = " ".join(parts).strip()
    if quoted:
        title = re.split(f"[{CLOSE_QUOTES}]", title.lstrip(OPEN_QUOTES))[0]
    else:
        title = cut_at_label(title, labels["stop_inline"], labels["stop_ambiguous"])
    # The source text is the lines of the title. A label alone on a line is not part of it.
    used = len(parts) - bool(first)
    source = lines[i : i + 1 + used] if first else lines[i + 1 : i + 1 + used]
    return (title.strip(), " ".join(source)) if title.strip() else None


def account_number(text: str) -> str:
    """The account as the document gives it, without spaces: with the country code if the document has one."""
    compact = re.sub(r"[\s-]", "", text).upper()
    if compact[:2].isalpha() and compact[:2] != "PL":
        return compact
    return ("PL" if compact.startswith("PL") else "") + common.digits(compact)[-26:]


def find_accounts(lines: list[str], labels: dict) -> dict[str, tuple[str, str]]:
    """Give the account of the sender and of the recipient, with the source text.

    The keyword that stands nearest before the account gives the role.
    """
    flat = " ".join(lines)
    patterns = {role: re.compile(labels[role][0], re.IGNORECASE) for role in ("z_rachunku", "na_rachunek")}
    result: dict[str, tuple[str, str]] = {}
    free = []
    for m in ACCOUNT.finditer(flat):
        # The organizer wants the number as the document gives it: with "PL" if the document has it.
        number = account_number(m.group(0))
        context = flat[max(0, m.start() - 250) : m.start()]
        nearest = {role: list(pattern.finditer(context))[-1:] for role, pattern in patterns.items()}
        hits = {role: k[0] for role, k in nearest.items() if k}
        role = max(hits, key=lambda r: hits[r].end()) if hits else None
        # The source text starts at the keyword when the role comes from a keyword.
        start = m.start() - len(context) + hits[role].start() if role else m.start() - 40
        found = (number, flat[max(start, m.end() - 150, 0) : m.end()])
        if role and role not in result:
            result[role] = found
        else:
            free.append(found)
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
    label_patterns = [
        p
        for key in ("data_operacji", "kwota", "numer_transakcji", "tytul", "z_rachunku", "na_rachunek", "other")
        for p in (labels.get(key, []))
    ]
    lines = merge_columns(prepare_lines(text), label_patterns)

    def put(name: str, found) -> None:
        if found:
            box[name], evidence[f"przelew_bankowy.{name}"] = found

    put("data_operacji", find_date(lines, labels))
    put("kwota", find_amount(lines, labels))
    reference = find_by_label(lines, labels["numer_transakcji"], parse_reference)
    if not reference:
        m = re.search(doc_type.raw.get("fallback", {}).get("numer_transakcji", r"(?!)"), text)
        reference = (m.group(0), m.group(0)) if m else None
    put("numer_transakcji", reference)
    put("tytul", find_title(lines, labels, box["numer_transakcji"]))
    for role, found in find_accounts(lines, labels).items():
        put(role, found)
    if not box["na_rachunek"]:
        put("na_rachunek", known_account(lines, doc_type.raw.get("known_accounts", [])))
    return data


def known_account(lines: list[str], accounts: list[str]) -> tuple[str, str] | None:
    """Repair an account that the OCR damaged, if it is near to a known account, for example of the UZP."""
    for line in lines:
        found = common.digits(line)
        if len(found) < 14:
            continue
        for account in accounts:
            if difflib.SequenceMatcher(None, found, account).ratio() >= 0.75:
                return ("PL" if re.search(r"\bPL\s*\d", line) else "") + account, line
    return None
