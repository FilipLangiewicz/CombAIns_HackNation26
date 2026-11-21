"""A data set of synthetic scans for the OCR path, with a split that has no data leakage.

Each document becomes page images. A degradation imitates a scan: rotation, blur, noise,
specks, punch holes, a dark edge and JPEG compression. The split follows the source:

| Split | Sources |
|---|---|
| train | organizer dev cases, synth seed 1 |
| val   | organizer negatywne, synth seed 3, real scans 0001-0004 |
| test  | organizer holdout cases, synth2 seed 101, real scans 0005-0010 |

The real scans with the same number are one case. Thus a case is in one split only.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from odw2json.evaluate import DATA, dataset, gold_for

DPI = 200
A4 = (1654, 2339)
MAX_PAGES = 4
LEVELS = ("light", "medium", "heavy")
FONT_DIRS = [Path("/usr/share/fonts/truetype"), Path("/usr/share/fonts")]


@dataclass
class Item:
    id: str
    split: str
    source: str
    gold: dict
    level: str  # "none" for a real scan
    pdf: Path | None = None
    text: str | None = None
    meta: dict = field(default_factory=dict)


def real_scan_split(pdf: Path) -> str:
    return "val" if int(pdf.parent.name) <= 4 else "test"


def manifest(train_variants: int = 2) -> list[Item]:
    from odw2json import synth, synth2

    items: list[Item] = []

    def add(base: str, split: str, source: str, gold: dict, variants: int, **kw) -> None:
        for v in range(variants):
            level = LEVELS[(len(items) + v) % len(LEVELS)]
            items.append(Item(f"{base}#{v}", split, source, gold, level, **kw))

    for group, pdf in dataset("dev,holdout,negatywne"):
        split = {"dev": "train", "holdout": "test", "negatywne": "val"}[group]
        variants = train_variants if split == "train" else 1
        add(str(pdf.relative_to(DATA)), split, f"organizer-{group}", gold_for(pdf), variants, pdf=pdf)
    for split, module, seed, n in (("train", synth, 1, 20), ("val", synth, 3, 10), ("test", synth2, 101, 20)):
        for name, text, gold in module.generate(n, seed):
            add(
                f"{module.__name__.split('.')[-1]}-{seed}/{name}",
                split,
                module.__name__.split(".")[-1],
                gold,
                1,
                text=text,
            )
    for pdf in sorted((DATA / "skany").glob("*/*/*.pdf")):
        items.append(
            Item(str(pdf.relative_to(DATA)), real_scan_split(pdf), "real-scan", gold_for(pdf), "none", pdf=pdf)
        )
    return items


# --- rendering -----------------------------------------------------------------


def fonts() -> list[Path]:
    found = []
    for folder in FONT_DIRS:
        found += [p for p in folder.rglob("*.ttf") if "Bold" not in p.name and "Oblique" not in p.name]
    return sorted(found)[:12] or [None]


def render_pdf(pdf: Path) -> list[Image.Image]:
    doc = pdfium.PdfDocument(str(pdf))
    pages = [doc[i].render(scale=DPI / 72).to_pil().convert("L") for i in range(min(len(doc), MAX_PAGES))]
    doc.close()
    return pages


def render_text(text: str, rng: random.Random) -> list[Image.Image]:
    """Draw plain text on A4 pages. The font, the size and the margins change from document to document."""
    path = rng.choice(fonts())
    size = rng.randint(26, 34)
    font = ImageFont.truetype(str(path), size) if path else ImageFont.load_default()
    margin, width = rng.randint(120, 200), A4[0]
    lines: list[str] = []
    for raw in text.split("\n"):
        words, current = raw.split(" "), ""
        for word in words:
            trial = f"{current} {word}" if current else word
            if font.getlength(trial) > width - 2 * margin and current:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    step = int(size * rng.uniform(1.35, 1.6))
    per_page = (A4[1] - 2 * margin) // step
    pages = []
    for start in range(0, len(lines), per_page):
        page = Image.new("L", A4, 255)
        draw = ImageDraw.Draw(page)
        for k, line in enumerate(lines[start : start + per_page]):
            draw.text((margin, margin + k * step), line, fill=rng.randint(0, 40), font=font)
        pages.append(page)
    return pages[:MAX_PAGES]


# --- degradation ---------------------------------------------------------------


def degrade(page: Image.Image, level: str, rng: random.Random) -> Image.Image:
    strength = {"light": 0.4, "medium": 0.7, "heavy": 1.0}[level]
    img = page.convert("L")
    img = img.rotate(rng.uniform(-2.5, 2.5) * strength, resample=Image.BICUBIC, expand=False, fillcolor=255)
    if rng.random() < 0.6 * strength:
        w, h = img.size
        scale = rng.uniform(0.55, 0.8)
        img = img.resize((int(w * scale), int(h * scale)), Image.BILINEAR).resize((w, h), Image.BILINEAR)
    img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0, 1.3) * strength))
    arr = np.asarray(img, dtype=np.float32)
    arr = arr * rng.uniform(0.85, 1.0) + rng.uniform(0, 25) * strength
    arr += np.random.default_rng(rng.randint(0, 10**9)).normal(0, 12 * strength, arr.shape)
    h, w = arr.shape
    if rng.random() < strength:  # a dark edge of the scanner
        edge = int(w * rng.uniform(0.01, 0.04))
        arr[:, w - edge :] *= np.linspace(1, 0.2, edge)[None, :]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)
    for _ in range(int(rng.randint(5, 60) * strength)):  # specks
        x, y, r = rng.randrange(w), rng.randrange(h), rng.uniform(1, 3)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=rng.randint(0, 90))
    if rng.random() < 0.5 * strength:  # punch holes
        y = rng.randint(40, 120)
        for x in (int(w * 0.35), int(w * 0.6)):
            draw.ellipse((x - 30, y - 30, x + 30, y + 30), fill=10)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=int(rng.uniform(85, 35) if strength > 0.5 else rng.uniform(90, 70)))
    return Image.open(io.BytesIO(buffer.getvalue())).convert("L")


def page_images(item: Item) -> list[Image.Image]:
    """The page images of an item: a real scan as it is, other items rendered and degraded."""
    rng = random.Random(item.id)
    if item.level == "none":
        return render_pdf(item.pdf)
    pages = render_pdf(item.pdf) if item.pdf else render_text(item.text, rng)
    return [degrade(p, item.level, rng) for p in pages]


def ocr_shard(items: list[Item], out: Path) -> None:
    """Write one JSON line for each item: the OCR text of each page, the gold and the time."""
    import json
    import time

    from odw2json.ocr import ocr_image

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        for n, item in enumerate(items, 1):
            start = time.time()
            pages = [ocr_image(p) for p in page_images(item)]
            row = {"id": item.id, "split": item.split, "source": item.source, "level": item.level,
                   "gold": item.gold, "pages": pages, "seconds": round(time.time() - start, 2)}  # fmt: skip
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{n}/{len(items)} {item.id} {row['seconds']} s", flush=True)


def report(paths: list[Path], split: str | None, errors: bool) -> None:
    """F1 of the OCR path for each split, source and level, from the JSON Lines files of ocr_shard."""
    import json
    from collections import defaultdict

    from odw2json.evaluate import Score, compare, doc_type
    from odw2json.ocr import repair
    from odw2json.pdftext import clean
    from odw2json.pipeline import process_text

    rows = [json.loads(line) for path in paths for line in path.read_text(encoding="utf-8").splitlines()]
    rows = [r for r in rows if split is None or r["split"] == split]
    groups: dict[str, Score] = defaultdict(Score)
    wrong_type, problems = [], []
    for r in rows:
        pred = process_text(clean("\n".join(repair(page) for page in r["pages"]))).data
        leaves = compare(r["gold"], pred)
        for key in ("ALL", r["split"], f"{r['split']}/{r['source']}", f"{r['split']}/level={r['level']}",
                    f"{r['split']}/type={doc_type(r['gold'])}"):  # fmt: skip
            groups[key].add(leaves)
        if doc_type(r["gold"]) != doc_type(pred):
            wrong_type.append(f"{r['id']}: {doc_type(r['gold'])} -> {doc_type(pred)}")
        problems += [(r["id"], leaf) for leaf in leaves if leaf.outcome in ("FP", "FN", "WRONG")]
    print(
        f"documents: {len(rows)}, seconds of OCR per document: {sum(r['seconds'] for r in rows) / max(len(rows), 1):.1f}"
    )
    for key in sorted(groups):
        print(f"{key:40s} {groups[key].line()}")
    print(f"wrong type: {len(wrong_type)}")
    for line in wrong_type[:20]:
        print("  " + line)
    if errors:
        for doc_id, leaf in problems:
            print(f"  {leaf.outcome:5s} {doc_id} {leaf.path}: gold={leaf.ref!r} pred={leaf.pred!r}")


def main() -> None:
    import argparse
    from collections import Counter

    parser = argparse.ArgumentParser(description="Show the OCR data set, save sample images, or make the OCR text.")
    parser.add_argument("--samples", type=Path, help="save the first page of some items to this folder")
    parser.add_argument("--shard", type=int, help="make the OCR text of this shard of the items")
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--split", help="only the items of this split")
    parser.add_argument("--out", type=Path, help="the JSON Lines file for --shard")
    parser.add_argument("--report", type=Path, nargs="+", help="give the F1 of these JSON Lines files")
    parser.add_argument("--errors", action="store_true", help="with --report: show each wrong field")
    args = parser.parse_args()
    if args.report:
        report(args.report, args.split, args.errors)
        return
    items = manifest()
    if args.split:
        items = [i for i in items if i.split == args.split]
    if args.shard is not None:
        ocr_shard(items[args.shard :: args.shards], args.out)
        return
    print(Counter((i.split, i.source) for i in items))
    if args.samples:
        args.samples.mkdir(parents=True, exist_ok=True)
        for item in items[:: max(len(items) // 12, 1)]:
            page_images(item)[0].save(args.samples / (item.id.replace("/", "_").replace("#", "_") + ".jpg"))


if __name__ == "__main__":
    main()
