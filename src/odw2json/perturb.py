"""A local robustness test: change the text of the examples and keep the expected values.

Each transform changes the form of the text but not the data, for example a NIP with
hyphens or a date in another format. A drop of the F1 score shows a weak rule.

Start: PYTHONPATH=src python -m odw2json.perturb --split dev
"""

from __future__ import annotations

import argparse
import random
import re
from collections import defaultdict

from odw2json.evaluate import Score, compare, dataset, doc_type, gold_for
from odw2json.pdftext import clean, read_pdf
from odw2json.pipeline import process_text

GENITIVE = dict(
    enumerate(
        [
            "stycznia",
            "lutego",
            "marca",
            "kwietnia",
            "maja",
            "czerwca",
            "lipca",
            "sierpnia",
            "września",
            "października",
            "listopada",
            "grudnia",
        ],
        1,
    )
)


def nip_hyphens(text: str, rng: random.Random) -> str:
    def fmt(m: re.Match) -> str:
        d = m.group(2)
        return m.group(1) + rng.choice([f"{d[:3]}-{d[3:6]}-{d[6:8]}-{d[8:]}", f"{d[:3]}-{d[3:5]}-{d[5:7]}-{d[7:]}"])

    return re.sub(r"(NIP:?\s*)(\d{10})(?!\d)", fmt, text)


def account_groups(text: str, rng: random.Random) -> str:
    def fmt(m: re.Match) -> str:
        d = re.sub(r"\D", "", m.group(0))
        grouped = d[:2] + " " + " ".join(d[i : i + 4] for i in range(2, 26, 4))
        return rng.choice(["PL" + grouped, grouped, "PL " + grouped, d, "PL" + d])

    return re.sub(r"(?<![\w])(?:PL\s?)?\d{2}(?:\s?\d{4}){6}(?!\d)", fmt, text)


def date_formats(text: str, rng: random.Random) -> str:
    def iso(m: re.Match) -> str:
        y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
        return rng.choice([f"{d:02d}.{mo:02d}.{y}", f"{d} {GENITIVE[mo]} {y}", f"{d:02d}-{mo:02d}-{y}", m.group(0)])

    def dotted(m: re.Match) -> str:
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            return m.group(0)
        return rng.choice([f"{d} {GENITIVE[mo]} {y}", f"{y}-{mo:02d}-{d:02d}", f"{d:02d}/{mo:02d}/{y}", m.group(0)])

    text = re.sub(r"(?<![\d.])(\d{4})-(\d{2})-(\d{2})(?![\d])", iso, text)
    return re.sub(r"(?<![\d.])(\d{2})\.(\d{2})\.(\d{4})(?![\d.])", dotted, text)


def amount_forms(text: str, rng: random.Random) -> str:
    def fmt(m: re.Match) -> str:
        whole, frac = m.group(1).replace(" ", ""), m.group(2)
        spaced = f"{int(whole):,}".replace(",", " ")
        return rng.choice(
            [f"{spaced},{frac} zł", f"{spaced},{frac} PLN", f"{whole}.{frac} PLN", f"{spaced},{frac} PLN"]
        )

    return re.sub(r"(\d[\d ]*),(\d{2})\s*(?:PLN|zł)", fmt, text)


def upper_labels(text: str, rng: random.Random) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.endswith(":") and len(line) < 30 and rng.random() < 0.7:
            lines[i] = line.upper()
    return "\n".join(lines)


def wrap_lines(text: str, rng: random.Random) -> str:
    out = []
    for line in text.split("\n"):
        spaces = [m.start() for m in re.finditer(" ", line)]
        if len(line) > 50 and spaces and rng.random() < 0.3:
            cut = rng.choice(spaces[len(spaces) // 3 :])
            out += [line[:cut], line[cut + 1 :]]
        else:
            out.append(line)
    return "\n".join(out)


def join_lines(text: str, rng: random.Random) -> str:
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        if i + 1 < len(lines) and len(lines[i]) < 40 and lines[i] and lines[i + 1] and rng.random() < 0.15:
            out.append(lines[i] + " " + lines[i + 1])
            i += 2
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def plain_quotes(text: str, rng: random.Random) -> str:
    return text.replace("„", '"').replace("”", '"') if rng.random() < 0.5 else text.replace("„", "«").replace("”", "»")


def page_markers(text: str, rng: random.Random) -> str:
    lines = text.split("\n")
    pos = rng.randrange(len(lines) // 3, max(len(lines) // 3 + 1, 2 * len(lines) // 3))
    marker = rng.choice(["Strona 1 z 3", "- 1 -", "1/2", "Str. 1"])
    return "\n".join(lines[:pos] + [marker] + lines[pos:])


TRANSFORMS = {
    "nip_hyphens": nip_hyphens,
    "account_groups": account_groups,
    "date_formats": date_formats,
    "amount_forms": amount_forms,
    "upper_labels": upper_labels,
    "wrap_lines": wrap_lines,
    "join_lines": join_lines,
    "plain_quotes": plain_quotes,
    "page_markers": page_markers,
}


def perturb(text: str, names: list[str], rng: random.Random) -> str:
    for name in names:
        text = TRANSFORMS[name](text, rng)
    return clean(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure the F1 score on changed copies of the examples.")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--seeds", type=int, default=3, help="the number of random copies for each document")
    parser.add_argument("--only", help="a comma-separated list of transforms")
    parser.add_argument("--errors", action="store_true")
    args = parser.parse_args()

    docs = [(p, read_pdf(p).text, gold_for(p)) for _, p in dataset(args.split)]
    variants = {name: [name] for name in TRANSFORMS}
    variants["ALL"] = list(TRANSFORMS)
    if args.only:
        variants = {name: names for name, names in variants.items() if name in args.only.split(",")}
    for name, names in variants.items():
        score, by_type, errors = Score(), defaultdict(Score), []
        for seed in range(args.seeds):
            for path, text, gold in docs:
                pred = process_text(perturb(text, names, random.Random(f"{seed}{path}")), path).data
                leaves = compare(gold, pred)
                score.add(leaves)
                by_type[doc_type(gold)].add(leaves)
                errors += [(path, leaf) for leaf in leaves if leaf.outcome in ("FP", "FN", "WRONG")]
        types = " ".join(f"{t}={s.f1:.3f}" for t, s in sorted(by_type.items()) if t != "none")
        print(f"{name:15s} F1={score.f1:.4f}  {types}")
        if args.errors:
            for path, leaf in errors[:15]:
                print(
                    f"    {leaf.outcome} {path.parent.name}/{path.name} {leaf.path} gold={leaf.ref!r} pred={leaf.pred!r}"
                )


if __name__ == "__main__":
    main()
