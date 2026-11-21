"""OCR of a page image with RapidOCR, with a cache on the disk.

RapidOCR installs with pip only (ONNX Runtime). Thus the test machine needs no system program.
"""

from __future__ import annotations

import hashlib
import io
import itertools
import json
import os
import re
import unicodedata
from functools import cache
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(os.environ.get("ODW2JSON_OCR_CACHE", ROOT / "data" / "cache" / "ocr"))
# On the 30 real scans, the default model (PP-OCRv6) found more values than the model for Latin scripts.
LANG = os.environ.get("ODW2JSON_OCR_LANG", "default")
DPI = 200
# Change this number when the OCR steps change, so that the cache gives no old results.
OCR_VERSION = 5


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
    width = max((b[2] for b in boxes), default=1)
    rows = [segments(sorted(line, key=lambda i: i[0]), width) for line in lines]
    out: list[str] = []
    i = 0
    while i < len(rows):
        # Two or more rows with two parts at the same place form two columns, for example two signature blocks.
        # The text layer of a PDF gives the left column first. The OCR text does the same.
        j = i
        while j < len(rows) and len(rows[j]) == 2 and abs(rows[j][1][0][0] - rows[i][1][0][0]) < COLUMN_ALIGN * width:
            j += 1
        if COLUMNS and j - i >= 2:
            out += [text_of(r[0]) for r in rows[i:j]] + [text_of(r[1]) for r in rows[i:j]]
            i = j
        else:
            out.append("  ".join(text_of(s) for s in rows[i]))
            i += 1
    return "\n".join(out)


COLUMNS = os.environ.get("ODW2JSON_OCR_COLUMNS", "1") == "1"
COLUMN_GAP = 0.05  # a gap wider than this part of the page width splits a row into parts
COLUMN_ALIGN = 0.06


def segments(line: list[list], width: float) -> list[list[list]]:
    parts = [[line[0]]]
    for box in line[1:]:
        if box[0] - parts[-1][-1][2] > COLUMN_GAP * width:
            parts.append([box])
        else:
            parts[-1].append(box)
    return parts


def text_of(part: list[list]) -> str:
    return "  ".join(b[4] for b in part)


def skew_angle(image: Image.Image) -> float:
    """Find the rotation of a scan in degrees with the projection profile.

    The rows of text give the sharpest profile of dark pixels when the page is straight.
    """

    small = image.convert("L")
    small = small.resize((small.width // 4, small.height // 4))
    best, best_score = 0.0, -1.0
    for angle in np.arange(-3.0, 3.01, 0.25):
        rotated = np.asarray(small.rotate(float(angle), fillcolor=255), dtype=np.float32)
        profile = (rotated < 128).sum(axis=1).astype(np.float32)
        score = float(np.square(np.diff(profile)).sum())
        if score > best_score:
            best, best_score = float(angle), score
    return best


def deskew(image: Image.Image) -> Image.Image:
    angle = skew_angle(image)
    return image if angle == 0 else image.rotate(angle, resample=Image.BICUBIC, fillcolor="white")


DESKEW = os.environ.get("ODW2JSON_OCR_DESKEW", "1") == "1"


# The recognition model gives wrong text for some long lines. A long box is split at the gaps between words.
MAX_PART_WIDTH = 500
NOT_LATIN = re.compile(r"[^\x00-\u024f\u2010-\u203a\u20ac]")


def split_points(gray, max_width: int = MAX_PART_WIDTH) -> list[int]:
    """Cut points of a text box: in the widest gap without ink in each part of the allowed width."""
    ink = (gray < 128).sum(axis=0)
    width, cuts = len(ink), [0]
    while width - cuts[-1] > max_width:
        low, high = cuts[-1] + max_width // 2, min(cuts[-1] + max_width, width - 1)
        best, best_len, run = None, 0, 0
        for k, value in enumerate(ink[low:high]):
            run = run + 1 if value == 0 else 0
            if run > best_len:
                best, best_len = k - run // 2, run
        # A cut inside a word breaks the word. Without a gap between words, the box stays whole.
        if best is None or best_len < MIN_GAP:
            break
        cuts.append(low + best)
    return [*cuts, width]


MIN_GAP = 6  # pixels without ink: a gap between words, not between letters


def ocr_boxes(image: Image.Image) -> list[list]:
    """The text boxes of an image as [x0, y0, x1, y1, text], with a cache on the disk."""
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    key = hashlib.sha1(buffer.getvalue() + f"{OCR_VERSION}{LANG}{DESKEW}{MAX_PART_WIDTH}".encode()).hexdigest()
    cached = CACHE_DIR / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    if DESKEW:
        image = deskew(image)
    rgb = np.array(image.convert("RGB"))
    gray = np.array(image.convert("L"))
    detected = engine()(rgb, use_det=True, use_cls=False, use_rec=False)
    regions = []
    for box in detected.boxes if detected.boxes is not None else []:
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        regions.append((max(0, round(min(xs))), max(0, round(min(ys))), round(max(xs)), round(max(ys))))
    boxes = []
    for region in regions:
        text = recognize(rgb, gray, region)
        if text:
            boxes.append([*region, text])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(boxes, ensure_ascii=False), encoding="utf-8")
    return boxes


def recognize(rgb, gray, box: tuple[int, int, int, int]) -> str:
    # One call for each part. A batch of all parts of a page was slower on the CPU.
    x0, y0, x1, y1 = box
    parts = []
    for a, b in itertools.pairwise(split_points(gray[y0:y1, x0:x1])):
        result = engine()(rgb[y0:y1, x0 + a : x0 + b], use_det=False, use_cls=False, use_rec=True)
        parts.append("".join(result.txts or []))
    return NOT_LATIN.sub("", " ".join(p for p in parts if p)).strip()


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

    text = re.sub(r"[^\W\d_]{3,}", fix, text)
    text = re.sub(r"[^\W\d_]{4,}(?=\s*:)", fix_keyword, text)  # only a label: a word before a colon
    # Words that the OCR joins: "zsiedzibą", "wBiałystok", "Serwisspółka".
    text = re.sub(r"\b([zw])(siedzibą|[A-ZŁŚŻŹĆ][a-ząćęłńóśźż]+)", r"\1 \2", text)
    text = re.sub(r"(?<=[a-ząćęłńóśźż])(spółk[aąi]|sp\.)(?=\s)", r" \1", text)
    # Typical letter errors of the OCR: a zero in "sp. z o.o.", a capital I for a small l inside a word.
    text = re.sub(r"\bsp\.\s?[zZ]\s?[oO0]\.\s?[oO0]\.", "sp. z o.o.", text)
    text = re.sub(r"(?<=[^\W\d_])I(?=[a-ząćęłńóśźż])", "l", text)
    return repair_emails(text)


# Label words of the documents. A word with one wrong letter becomes the label word, for example "Tytut" becomes "Tytuł".
KEYWORDS = [
    "Tytuł", "Tytułem", "Kwota", "Kwoty", "Rachunek", "Rachunku", "Odbiorca", "Odbiorcy", "Nadawca", "Nadawcy",
    "Odwołujący", "Odwołującego", "Zamawiający", "Zamawiającego", "Pełnomocnik", "Pełnomocnika", "Pełnomocnicy",
    "Mocodawca", "Mocodawcy", "Pełnomocnictwo", "Odwołanie", "Operacji", "Transakcji", "Dotyczy", "Zarzut", "Opis",
]  # fmt: skip


def fix_keyword(m: re.Match) -> str:
    token = m.group(0)
    low = fold(token).lower()
    for word in KEYWORDS:
        target = fold(word).lower()
        if low != target and len(low) == len(target) and sum(a != b for a, b in zip(low, target, strict=True)) == 1:
            return same_case(word, token)
    return token


TOP_DOMAINS = {"pl", "com", "eu", "org", "net", "info", "biz", "gov", "edu", "example"}


def repair_emails(text: str) -> str:
    """Remove the spaces that the OCR puts into an e-mail address."""
    text = re.sub(r"(?<=\w)[ \t]*@[ \t]*(?=\w)", "@", text)
    # A short part before the address: "bi uro@firma.pl".
    text = re.sub(r"(?<=[\s,:])([a-z]{1,3}) (?=[\w.\-]+@[\w\-]+\.)", r"\1", text)

    def join_domain(m: re.Match) -> str:
        joined = m.group(2) + m.group(3)
        return m.group(1) + joined if joined.lower() in TOP_DOMAINS else m.group(0)

    # A broken top domain: "biuro@firma.exam ple".
    return re.sub(r"(@[\w\-]+(?:\.[\w\-]+)*\.)([a-z]+) ([a-z]{1,5})\b", join_domain, text)


def ocr_page(page) -> str:
    """OCR of a pypdfium2 page, with the repair of the diacritics."""
    return repair(ocr_image(page.render(scale=DPI / 72).to_pil()))
