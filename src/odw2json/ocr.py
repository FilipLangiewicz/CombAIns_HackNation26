"""OCR of a page image with RapidOCR, with a cache on the disk.

RapidOCR installs with pip only (ONNX Runtime). Thus the test machine needs no system program.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import unicodedata
from functools import cache
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(os.environ.get("ODW2JSON_OCR_CACHE", ROOT / "data" / "cache" / "ocr"))
# On the 30 real scans, the default model (PP-OCRv6) found more values than the model for Latin scripts.
LANG = os.environ.get("ODW2JSON_OCR_LANG", "default")
DPI = 200


def available() -> bool:
    try:
        import rapidocr  # noqa: F401
    except ImportError:
        return False
    return True


@cache
def engine():
    from rapidocr import LangRec, OCRVersion, RapidOCR

    params = {"Global.log_level": "error"}
    if LANG == "latin":
        params |= {"Rec.lang_type": LangRec.LATIN, "Rec.ocr_version": OCRVersion.PPOCRV5}
    if os.environ.get("ODW2JSON_OCR_THREADS"):
        params |= {"EngineConfig.onnxruntime.intra_op_num_threads": int(os.environ["ODW2JSON_OCR_THREADS"])}
    return RapidOCR(params=params)


def boxes_to_lines(boxes: list[list]) -> str:
    """Join the text boxes [x0, y0, x1, y1, text] into lines: boxes with a similar vertical center form one line."""
    items = sorted(boxes, key=lambda b: (b[1] + b[3]) / 2)
    lines: list[list[list]] = []
    for item in items:
        center = (item[1] + item[3]) / 2
        if lines:
            last = lines[-1]
            top = sum(i[1] for i in last) / len(last)
            bottom = sum(i[3] for i in last) / len(last)
            # A box belongs to the line if its center is in the middle part of the line height.
            if top + (bottom - top) * 0.25 <= center <= bottom - (bottom - top) * 0.25:
                last.append(item)
                continue
        lines.append([item])
    return "\n".join("  ".join(i[4] for i in sorted(line, key=lambda i: i[0])) for line in lines)


def ocr_boxes(image: Image.Image) -> list[list]:
    """The text boxes of an image as [x0, y0, x1, y1, text], with a cache on the disk."""
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    key = hashlib.sha1(buffer.getvalue() + LANG.encode()).hexdigest()
    cached = CACHE_DIR / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    import numpy as np

    result = engine()(np.array(image.convert("RGB")))
    boxes = []
    for box, text in zip(result.boxes if result.txts else [], result.txts or [], strict=True):
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        boxes.append([round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys)), text])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(boxes, ensure_ascii=False), encoding="utf-8")
    return boxes


def ocr_image(image: Image.Image) -> str:
    return boxes_to_lines(ocr_boxes(image))


def fold(text: str) -> str:
    """Remove the Polish diacritics, for example "Odwołujący" becomes "Odwolujacy"."""
    text = text.replace("ł", "l").replace("Ł", "L")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


@cache
def diacritic_words() -> dict[str, str]:
    path = ROOT / "config" / "ocr_words.txt"
    words = [w for w in path.read_text(encoding="utf-8").split() if not w.startswith("#")] if path.exists() else []
    return {fold(w): w for w in words}


def same_case(word: str, model: str) -> str:
    if model.isupper():
        return word.upper()
    if model[:1].isupper():
        return word[:1].upper() + word[1:]
    return word


def repair(text: str) -> str:
    """Restore the diacritics that the OCR lost. A word changes only if the vocabulary has one form for it."""
    words = diacritic_words()

    def fix(m: re.Match) -> str:
        token = m.group(0)
        known = words.get(fold(token).lower())
        return same_case(known, token) if known else token

    return re.sub(r"[^\W\d_]{3,}", fix, text)


def ocr_page(page) -> str:
    """OCR of a pypdfium2 page, with the repair of the diacritics."""
    return repair(ocr_image(page.render(scale=DPI / 72).to_pil()))
