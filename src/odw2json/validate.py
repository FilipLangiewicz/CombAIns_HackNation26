"""Field validation from the key "validate" of a type configuration.

Each rule has these keys:
- path: the field, for example "Odwolujacy[].nip" or "przelew_bankowy.kwota". "[]" means each item of a list.
- kind: digits, date, email, amount or regex.
- lengths: for kind "digits", the allowed numbers of digits, for example [9, 14].
- pattern: for kind "regex", the value must match it completely.
- checksum: for kind "digits", "nip", "regon" or "pesel" (optional). The example data is synthetic, so the default is none.

A value that is not valid becomes null, and the result gets a warning.
For kind "digits", the typical OCR errors in digits are repaired first: O to 0, l and I to 1.
"""

from __future__ import annotations

import re
from datetime import date

OCR_DIGITS = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "|": "1", "S": "5", "B": "8"})
WEIGHTS = {
    "nip": [6, 5, 7, 2, 3, 4, 5, 6, 7],
    "regon": [8, 9, 2, 3, 4, 5, 6, 7],
    "pesel": [1, 3, 7, 9, 1, 3, 7, 9, 1, 3],
}


def checksum_ok(value: str, kind: str) -> bool:
    w = WEIGHTS[kind]
    if len(value) < len(w) + 1:
        return False
    total = sum(int(d) * k for d, k in zip(value, w, strict=False))
    if kind == "pesel":
        return (10 - total % 10) % 10 == int(value[10])
    return total % 11 % 10 == int(value[len(w)]) if kind == "regon" else total % 11 == int(value[9])


def check(value, rule: dict) -> tuple[object, str | None]:
    """Give the repaired value, or None and the reason."""
    kind = rule.get("kind", "regex")
    if kind == "digits":
        text = re.sub(r"[\s\-]", "", str(value)).translate(OCR_DIGITS)
        if not text.isdigit() or ("lengths" in rule and len(text) not in rule["lengths"]):
            return None, f"not {rule.get('lengths', '')} digits: {value!r}"
        if rule.get("checksum") and not checksum_ok(text, rule["checksum"]):
            return None, f"wrong {rule['checksum']} checksum: {value!r}"
        return text, None
    if kind == "date":
        try:
            date.fromisoformat(str(value))
        except ValueError:
            return None, f"not a date YYYY-MM-DD: {value!r}"
        return value, None
    if kind == "email":
        ok = re.fullmatch(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+", str(value))
        return (value, None) if ok else (None, f"not an e-mail address: {value!r}")
    if kind == "amount":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
        return (value, None) if ok else (None, f"not a positive amount: {value!r}")
    ok = re.fullmatch(rule["pattern"], str(value))
    return (value, None) if ok else (None, f"does not match {rule['pattern']}: {value!r}")


def apply(data: dict, rules: list[dict]) -> list[str]:
    """Validate the fields in place. Give the warnings."""
    warnings: list[str] = []
    for rule in rules:
        for parent, key, shown in locate(data, rule["path"].split("."), ""):
            value = parent.get(key)
            if value is None:
                continue
            new, reason = check(value, rule)
            parent[key] = new
            if reason:
                warnings.append(f"{shown}: {reason}")
    return warnings


def locate(node, keys: list[str], shown: str):
    """Give (parent dict, key, path) for each field of the path. "name[]" goes into each item of a list."""
    if not isinstance(node, dict) or not keys:
        return
    key, rest = keys[0], keys[1:]
    if key.endswith("[]"):
        for i, item in enumerate(node.get(key[:-2]) or []):
            yield from locate(item, rest, f"{shown}{key[:-2]}[{i}].")
    elif not rest:
        if key in node:
            yield node, key, f"{shown}{key}"
    else:
        yield from locate(node.get(key), rest, f"{shown}{key}.")
