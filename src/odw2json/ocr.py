"""OCR of a page image with RapidOCR, with a cache on the disk.

RapidOCR installs with pip only (ONNX Runtime). Thus the test machine needs no system program.
"""

from __future__ import annotations

import hashlib
import io
import os
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
    if os.environ.get("ODW2JSON_OCR_CUDA"):
        params |= {"EngineConfig.onnxruntime.use_cuda": True}
    return RapidOCR(params=params)


def boxes_to_lines(boxes, texts) -> str:
    """Join the text boxes into lines: boxes with a similar vertical center form one line, from left to right."""
    items = []
    for box, text in zip(boxes, texts, strict=True):
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append((min(ys), max(ys), min(xs), text))
    items.sort(key=lambda i: (i[0] + i[1]) / 2)
    lines: list[list[tuple]] = []
    for item in items:
        center = (item[0] + item[1]) / 2
        if lines:
            last = lines[-1]
            top = sum(i[0] for i in last) / len(last)
            bottom = sum(i[1] for i in last) / len(last)
            # A box belongs to the line if its center is in the middle part of the line height.
            if top + (bottom - top) * 0.25 <= center <= bottom - (bottom - top) * 0.25:
                last.append(item)
                continue
        lines.append([item])
    return "\n".join("  ".join(i[3] for i in sorted(line, key=lambda i: i[2])) for line in lines)


def ocr_image(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    key = hashlib.sha1(buffer.getvalue() + LANG.encode()).hexdigest()
    cached = CACHE_DIR / f"{key}.txt"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    import numpy as np

    result = engine()(np.array(image.convert("RGB")))
    text = boxes_to_lines(result.boxes, result.txts) if result.txts else ""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_text(text, encoding="utf-8")
    return text


def ocr_page(page) -> str:
    """OCR of a pypdfium2 page."""
    return ocr_image(page.render(scale=DPI / 72).to_pil())
