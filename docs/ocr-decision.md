# OCR decision

This file tells how the application decides if a PDF page needs OCR.

## The rule

The code is in `src/odw2json/pdftext.py`.

1. The application reads the text layer of each page with pypdfium2.
2. If a page has fewer than 30 characters after the removal of spaces (`MIN_PAGE_CHARS`), the page has no usable text layer.
3. Such a page goes to OCR: the application renders the page at 300 DPI and gives the image to Tesseract with the Polish language data (`pol`).
4. If Tesseract is not installed, the page text stays empty and the result marks the document with `ocr_missing`. The CLI shows "no text layer and no OCR engine".

The decision is for each page, not for each document. Thus a document with a scanned attachment page gets OCR only for that page.

## Why this rule

- In the example data, each page of a PDF with a text layer has hundreds of characters. Each page of a scan has 0 to 3 characters.
- A count of characters is fast and needs no model.

## Limits and what we do about them

| Limit | Effect | What we do |
|---|---|---|
| A scan with a bad text layer from an old OCR (wrong letters, many characters) | The page is not sent to OCR. The extraction gets bad text. | Not handled yet. A possible check: the part of the text that is Polish words. |
| A page with only a stamp or a short note | The page goes to OCR without need. | No problem: OCR on a short page is fast. |
| Tesseract needs a system installation | The test machine can have no Tesseract. | Open item. RapidOCR installs with pip only and is a candidate. |

## Status

OCR is not the main work now. The 30 scans in `dane/skany/` are not in the F1 result yet. The team decides about OCR after a talk with the organizer.
