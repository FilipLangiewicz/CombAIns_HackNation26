# OCR

This file tells how the application decides if a PDF page needs OCR, and how the OCR path operates.

## The decision

The code is in `src/odw2json/pdftext.py`.

1. The application reads the text layer of each page with pypdfium2.
2. If a page has fewer than 30 characters without the spaces at its start and end (`MIN_PAGE_CHARS`), the page has no usable text layer.
3. Such a page goes to OCR (`ocr.ocr_page`). If RapidOCR is not installed, the page text stays empty, and the result marks the document with `ocr_missing`.

4. The OCR reads the first 3 scanned pages (`ODW2JSON_OCR_MAX_PAGES`). Then the application finds the type:
   - If the type has `ocr_first_pages_only: true` (the appeal), the OCR stops. If a field in `ocr_more_pages_if_empty` is empty, the OCR reads all pages and fills only the empty fields.
   - For the other types, the OCR reads all pages, because a power of attorney has the signatures on its last page.

The decision is for each page, not for each document. In the example data, each page with a text layer has hundreds of characters, and each page of a scan has 0 to 3 characters.

## The OCR path

The code is in `src/odw2json/ocr.py`.

1. **Image:** the page is rendered at 200 DPI. The scans of the organizer have this resolution.
2. **Rotation:** the projection profile gives the rotation of the page between -3 and +3 degrees, in steps of 0.25 degrees. The page is rotated back. A rotated page gives lines that mix two columns and broken words.
3. **OCR:** RapidOCR with the default model PP-OCRv6 gives text boxes. RapidOCR installs with pip only, so the test machine needs no system program. On the 30 real scans, the default model found 78% of the gold values in the text, and the model for Latin scripts found 68%.
4. **Lines:** boxes with a similar vertical center form one line, from left to right.
5. **Columns:** a gap wider than 5% of the page width splits a row into parts. Two or more rows with two parts at the same place are two columns, for example two signature blocks. The left column comes first, as in the text layer of a PDF.
6. **Diacritics:** the OCR can lose the Polish diacritics. A word without diacritics gets them back if `config/ocr_words.txt` has exactly one form for it, for example "Odwolujacy" becomes "Odwołujący". The vocabulary comes from the dev cases and the configuration. A word is in the vocabulary only if its form without diacritics is not a word of the dev texts. For example, "dostawa" and "dostawą" are both words, so "dostawa" does not change.
7. **Classification:** each classification rule also matches the text without diacritics (see `docs/classification.md`).
8. **Cache:** the boxes of each image are kept in `data/cache/ocr/`. A second run of the same image needs no OCR.

## The data set for the OCR path

The code is in `src/odw2json/scans.py`. The jobs on Kaggle make the OCR boxes (see `jobs/JOBS.md`).

| Split | Sources | Use |
|---|---|---|
| train | organizer dev cases (3 variants), generator 1 seed 1 | tune the rules |
| val | organizer negative documents, generator 1 seed 3, real scans 0001-0004 | select variants |
| test | organizer holdout cases, generator 2 seed 101, real scans 0005-0010 | final measurement only |

- A synthetic scan is a rendered page with a degradation at the level light, medium or heavy.
- The degradation has rotation, blur, noise, specks, punch holes, a dark edge and JPEG compression.
- The real scans with the same number are one case. Thus a case is in one split only.
- `python -m odw2json.scans --report <files>` gives the F1 for each split, source, level and type.
