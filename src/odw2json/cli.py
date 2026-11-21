"""The command line interface: input/<case>/<file>.pdf gives output/<case>/<file>.json."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from odw2json.pipeline import process_pdf

ROOT = Path(__file__).resolve().parents[2]


def process_one(pdf: Path) -> tuple[dict, str]:
    try:
        result = process_pdf(pdf)
        note = result.doc_type or "unknown type"
        if result.ocr_missing:
            note += " (no text layer and no OCR engine)"
        return result.data, note
    except Exception as exc:  # noqa: BLE001 - one bad file must not stop the other files.
        return {}, f"error: {exc}"


def init_worker(threads: int) -> None:
    os.environ["ODW2JSON_OCR_THREADS"] = str(threads)


def run(input_dir: Path, output_dir: Path, verbose: bool = False, workers: int = 0) -> int:
    pdfs = sorted(p for p in input_dir.rglob("*") if p.suffix.lower() == ".pdf")
    if not pdfs:
        print(f"No PDF files in {input_dir}", file=sys.stderr)
        return 1
    cores = os.cpu_count() or 1
    # The OCR of a page uses some cores well, so each process gets two or more cores.
    workers = workers or max(1, min(len(pdfs), cores // 2))
    start = time.time()
    with ProcessPoolExecutor(workers, initializer=init_worker, initargs=(max(1, cores // workers),)) as pool:
        for pdf, (data, note) in zip(pdfs, pool.map(process_one, pdfs), strict=True):
            target = output_dir / pdf.relative_to(input_dir).with_suffix(".json")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{pdf.relative_to(input_dir)} -> {target.relative_to(output_dir)}  [{note}]", flush=True)
            if verbose and data:
                print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"{len(pdfs)} files in {time.time() - start:.0f} s with {workers} processes")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read the PDF files of KIO appeal cases and write one JSON file for each."
    )
    parser.add_argument("--input", type=Path, default=ROOT / "input", help="the input folder (default: input/)")
    parser.add_argument("--output", type=Path, default=ROOT / "output", help="the output folder (default: output/)")
    parser.add_argument("-v", "--verbose", action="store_true", help="show the extracted data")
    parser.add_argument("--workers", type=int, default=0, help="the number of processes (default: cores / 2)")
    parser.add_argument("--gui", action="store_true", help="start the web interface")
    parser.add_argument("--port", type=int, default=8000, help="the port of the web interface (default: 8000)")
    parser.add_argument("--host", default="127.0.0.1", help="the address of the web interface (Docker: 0.0.0.0)")
    args = parser.parse_args()
    if args.gui:
        from odw2json.gui import serve

        serve(args.port, args.host)
        return
    sys.exit(run(args.input, args.output, args.verbose, args.workers))


if __name__ == "__main__":
    main()
