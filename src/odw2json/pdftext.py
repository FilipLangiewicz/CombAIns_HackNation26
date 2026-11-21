"""Read the text of a PDF file. Use OCR for a page without a text layer."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pypdfium2 as pdfium

from odw2json import ocr

# A page with fewer characters than this has no usable text layer.
MIN_PAGE_CHARS = 30
# The data of the known types is on the first pages. The pipeline reads later scanned pages only if a field is empty.
MAX_OCR_PAGES = int(os.environ.get("ODW2JSON_OCR_MAX_PAGES", "3"))


@dataclass
class Document:
    path: Path
    pages: list[str]
    ocr_pages: list[int] = field(default_factory=list)
    ocr_missing: bool = False
    skipped_pages: list[int] = field(default_factory=list)  # scanned pages without OCR

    @property
    def text(self) -> str:
        return "\n".join(self.pages)


def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(" ", " ").replace(" ", " ").replace(" ", " ")
    text = text.replace("￾", "").replace("­", "").replace("\x02", "-")
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.split("\n"))


def read_pdf(path: Path, max_ocr_pages: int | None = MAX_OCR_PAGES) -> Document:
    """Read all pages. Give OCR to the first max_ocr_pages scanned pages (None: all of them)."""
    pdf = pdfium.PdfDocument(str(path))
    doc = Document(Path(path), [])
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            text = page.get_textpage().get_text_range()
            if len(text.strip()) < MIN_PAGE_CHARS:
                if max_ocr_pages is not None and len(doc.ocr_pages) >= max_ocr_pages:
                    text = ""
                    doc.skipped_pages.append(i)
                elif ocr.available():
                    text = ocr.ocr_page(page)
                    doc.ocr_pages.append(i)
                else:
                    doc.ocr_missing = True
            doc.pages.append(clean(text))
    finally:
        pdf.close()
    return doc
