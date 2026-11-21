"""The command line interface: input/<case>/<file>.pdf gives output/<case>/<file>.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from odw2json.pipeline import process_pdf

ROOT = Path(__file__).resolve().parents[2]


def run(input_dir: Path, output_dir: Path, verbose: bool = False) -> int:
    pdfs = sorted(p for p in input_dir.rglob("*") if p.suffix.lower() == ".pdf")
    if not pdfs:
        print(f"No PDF files in {input_dir}", file=sys.stderr)
        return 1
    for pdf in pdfs:
        target = output_dir / pdf.relative_to(input_dir).with_suffix(".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = process_pdf(pdf)
            data = result.data
            note = result.doc_type or "unknown type"
            if result.ocr_missing:
                note += " (no text layer and no OCR engine)"
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the other files.
            data, note = {}, f"error: {exc}"
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{pdf.relative_to(input_dir)} -> {target.relative_to(output_dir)}  [{note}]")
        if verbose and data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read the PDF files of KIO appeal cases and write one JSON file for each."
    )
    parser.add_argument("--input", type=Path, default=ROOT / "input", help="the input folder (default: input/)")
    parser.add_argument("--output", type=Path, default=ROOT / "output", help="the output folder (default: output/)")
    parser.add_argument("-v", "--verbose", action="store_true", help="show the extracted data")
    parser.add_argument("--gui", action="store_true", help="start the web interface")
    parser.add_argument("--port", type=int, default=8000, help="the port of the web interface (default: 8000)")
    args = parser.parse_args()
    if args.gui:
        from odw2json.gui import serve

        serve(args.port)
        return
    sys.exit(run(args.input, args.output, args.verbose))


if __name__ == "__main__":
    main()
