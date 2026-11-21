"""Field-level F1 score with the rules of the organizer.

Rules (Discord, 2026-11-21):
- TP: the value is in our JSON and agrees with the reference.
- TN: the value is not in our JSON and not in the reference.
- FP: the value is only in our JSON, or it is in both but it is not correct.
- FN: the value is only in the reference.
- Long strings need an 80% agreement. All other values must agree exactly.
- The items of a list are matched by their content, not by their order.

The "strict" variant counts a wrong value as FP and FN. It is a lower bound,
because the organizer did not tell which variant the jury uses.
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

LONG_FIELDS = {
    "Odwolujacy[].nazwa",
    "Odwolujacy[].pelnomocnik.nazwa",
    "Zamawiajacy[].nazwa",
    "ZamowieniePubliczne.tytul",
    "przelew_bankowy.tytul",
}
LONG_THRESHOLD = 0.8

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "uzp" / "dane"
SPLIT_FILE = ROOT / "config" / "split.json"


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return 1.0 - levenshtein(a, b) / max(len(a), len(b))


def is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


ACCOUNT_FIELDS = {"przelew_bankowy.z_rachunku", "przelew_bankowy.na_rachunek"}


def values_agree(ref, pred, path: str) -> bool:
    # Some example files have an account without "PL" although the document has it. The organizer
    # told that this is an error of the examples (Discord, 2026-11-21). Thus the prefix is not compared.
    if path in ACCOUNT_FIELDS and isinstance(ref, str) and isinstance(pred, str):
        return ref.removeprefix("PL") == pred.removeprefix("PL")
    if is_number(ref) and is_number(pred):
        return abs(ref - pred) < 1e-9
    if path in LONG_FIELDS and isinstance(ref, str) and isinstance(pred, str):
        return similarity(ref, pred) >= LONG_THRESHOLD
    return type(ref) is type(pred) and ref == pred


@dataclass
class Leaf:
    path: str
    outcome: str  # TP, FP, FN, TN or WRONG (in both, not correct)
    ref: object = None
    pred: object = None


def compare(ref, pred, path: str = "") -> list[Leaf]:
    """Compare two JSON values. Give one Leaf for each scalar field."""
    if isinstance(ref, dict) or isinstance(pred, dict):
        ref = ref if isinstance(ref, dict) else {}
        pred = pred if isinstance(pred, dict) else {}
        leaves = []
        for key in list(ref) + [k for k in pred if k not in ref]:
            sub = f"{path}.{key}" if path else key
            leaves += compare(ref.get(key), pred.get(key), sub)
        return leaves
    if isinstance(ref, list) or isinstance(pred, list):
        return compare_lists(ref if isinstance(ref, list) else [], pred if isinstance(pred, list) else [], path + "[]")
    if ref is None and pred is None:
        return [Leaf(path, "TN")]
    if pred is None:
        return [Leaf(path, "FN", ref, pred)]
    if ref is None:
        return [Leaf(path, "FP", ref, pred)]
    return [Leaf(path, "TP" if values_agree(ref, pred, path) else "WRONG", ref, pred)]


def tp_count(leaves: list[Leaf]) -> int:
    return sum(leaf.outcome == "TP" for leaf in leaves)


def compare_lists(ref: list, pred: list, path: str) -> list[Leaf]:
    """Match the items with the assignment that gives the most TP fields."""
    n = max(len(ref), len(pred))
    ref_items = ref + [None] * (n - len(ref))
    pred_items = pred + [None] * (n - len(pred))
    cache = {}

    def pair(i, j):
        if (i, j) not in cache:
            cache[(i, j)] = compare(ref_items[i], pred_items[j], path)
        return cache[(i, j)]

    if n <= 7:
        best = max(itertools.permutations(range(n)), key=lambda p: sum(tp_count(pair(i, j)) for i, j in enumerate(p)))
    else:
        best, free = [], set(range(n))
        for i in range(n):
            j = max(free, key=lambda j: tp_count(pair(i, j)))
            best.append(j)
            free.remove(j)
    return [leaf for i, j in enumerate(best) for leaf in pair(i, j)]


@dataclass
class Score:
    counts: Counter = field(default_factory=Counter)

    def add(self, leaves: list[Leaf]) -> None:
        for leaf in leaves:
            self.counts[leaf.outcome] += 1

    @property
    def f1(self) -> float:
        c = self.counts
        tp, fp, fn = c["TP"], c["FP"] + c["WRONG"], c["FN"]
        return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0

    @property
    def f1_strict(self) -> float:
        c = self.counts
        tp, fp, fn = c["TP"], c["FP"] + c["WRONG"], c["FN"] + c["WRONG"]
        return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0

    def line(self) -> str:
        c = self.counts
        return (
            f"F1={self.f1:.4f} strict={self.f1_strict:.4f} "
            f"TP={c['TP']} FP={c['FP']} WRONG={c['WRONG']} FN={c['FN']} TN={c['TN']}"
        )


def doc_type(obj: dict) -> str:
    if not obj:
        return "none"
    if "OdwolanieKIO" in obj:
        return "odwolanie"
    if "mocodawca" in obj:
        return "pelnomocnictwo"
    if "przelew_bankowy" in obj:
        return "przelew"
    return "other"


# --- the data set ---------------------------------------------------------


def gold_for(pdf: Path) -> dict:
    """Find the expected JSON of a PDF file. A PDF without a JSON file expects {}."""
    candidates = [pdf.with_suffix(".json")]
    if pdf.stem == "potwierdzenie_przelewu":
        candidates.append(pdf.with_name("przelew.json"))
    for c in candidates:
        if c.exists():
            return json.loads(c.read_text(encoding="utf-8"))
    return {}


def dataset(split: str = "all") -> list[tuple[str, Path]]:
    """Give (group, pdf) pairs. The group is "dev", "holdout", "negatywne" or "skany"."""
    groups = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))
    items = []
    for group in ("dev", "holdout"):
        for case in groups[group]:
            items += [(group, p) for p in sorted((DATA / case).glob("*.pdf"))]
    items += [("negatywne", p) for p in sorted((DATA / "negatywne").glob("*.pdf"))]
    items += [("skany", p) for p in sorted((DATA / "skany").glob("*/*/*.pdf"))]
    if split == "all":
        return items
    wanted = set(split.split(","))
    return [(g, p) for g, p in items if g in wanted]


def evaluate(split: str, show_errors: bool, out_dir: Path | None) -> Score:
    from odw2json.pipeline import process_pdf

    total = Score()
    by_group: dict[str, Score] = defaultdict(Score)
    by_type: dict[str, Score] = defaultdict(Score)
    by_field: dict[str, Score] = defaultdict(Score)
    type_hits = Counter()
    errors = []
    start = time.time()
    items = dataset(split)
    for group, pdf in items:
        gold = gold_for(pdf)
        pred = process_pdf(pdf).data
        if out_dir:
            target = out_dir / pdf.relative_to(DATA).with_suffix(".json")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8")
        leaves = compare(gold, pred)
        total.add(leaves)
        by_group[group].add(leaves)
        by_type[doc_type(gold)].add(leaves)
        for leaf in leaves:
            by_field[leaf.path].add([leaf])
        type_hits[(doc_type(gold), doc_type(pred))] += 1
        rel = pdf.relative_to(DATA)
        errors += [(str(rel), leaf) for leaf in leaves if leaf.outcome in ("FP", "FN", "WRONG")]
    seconds = time.time() - start

    print(f"Documents: {len(items)}  time: {seconds:.1f} s ({seconds / max(len(items), 1):.2f} s per document)")
    print(f"TOTAL      {total.line()}")
    for name, score in sorted(by_group.items()):
        print(f"group {name:10s} {score.line()}")
    for name, score in sorted(by_type.items()):
        print(f"type  {name:10s} {score.line()}")
    print("Classification (gold -> predicted):")
    for (g, p), n in sorted(type_hits.items()):
        print(f"  {g:15s} -> {p:15s} {n}{'' if g == p else '   <-- error'}")
    print("Fields:")
    for name, score in sorted(by_field.items(), key=lambda kv: kv[1].f1):
        print(f"  {name:45s} {score.line()}")
    if show_errors:
        print("Errors:")
        for rel, leaf in errors:
            print(f"  {leaf.outcome:5s} {rel}  {leaf.path}\n        gold={leaf.ref!r}\n        pred={leaf.pred!r}")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure the F1 score on the example data of the organizer.")
    parser.add_argument("--split", default="dev", help="all, or a list of groups: dev,holdout,negatywne,skany")
    parser.add_argument("--errors", action="store_true", help="show each wrong field")
    parser.add_argument("--out", type=Path, help="write the predicted JSON files to this folder")
    args = parser.parse_args()
    evaluate(args.split, args.errors, args.out)


if __name__ == "__main__":
    main()
