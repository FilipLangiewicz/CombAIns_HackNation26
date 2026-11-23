# ⚖️ KIOsk

![Python 3.13](https://img.shields.io/badge/python-3.13-blue)
![F1 0.999](https://img.shields.io/badge/F1-0.999-brightgreen)
![No LLM](https://img.shields.io/badge/LLM-not%20used-lightgrey)
![License MIT](https://img.shields.io/badge/license-MIT-green)

KIOsk reads the PDF documents of a KIO appeal case and writes one JSON file for each document. It was made for the challenge "Odwołania2json" of HackNation 2026.

![The analysis page: the PDF file and the extracted fields with their source text](docs/presentation/img/analiza.png)

## How it works

- **Rules, not an LLM.** Each document type has weighted rules in `config/types/*.yaml`. The type with the most points wins if it reaches its threshold. A document of an unknown type gives `{}`.
- **OCR for scans.** A page without a text layer goes to RapidOCR. The models are in the `pip` package, so the run needs no internet.
- **New type without code.** To add a document type, add a YAML file.
- **Explained decisions.** The web interface shows the source text of each value and the path of each document.

![The path of a scanned document: OCR, classification, extraction and validation](docs/presentation/img/graph_scan.png)

## Results

All measurements ran on a CPU without a GPU.

| Test set | Files | F1 |
|---|---|---|
| All PDF files of the challenge | 226 | 0.999 |
| Documents with a text layer, dev / holdout | 135 / 45 | 1.000 / 1.000 |
| Real scans (OCR) | 30 | 0.992 |
| Documents of an unknown type (expected `{}`) | 12 | 1.000 |

A PDF with a text layer takes approximately 0.01 s. A scan takes approximately 11 s.

## Quick start

To process a case with Docker, do these steps:

1. Put the PDF files into `input/<case>/`.
2. Run `docker compose run --rm cli`.
3. Read the JSON files in `output/<case>/`.

To start the web interface on http://127.0.0.1:8000, run `docker compose up`.

## Run without Docker

To run the application with Python 3.13, do these steps:

1. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

2. Process the files in `input/`:

   ```bash
   python main.py
   ```

3. Or start the web interface:

   ```bash
   python main.py --gui
   ```

Use `--input`, `--output` and `--workers` to change the folders and the number of processes.

## Development

To measure the quality, do these steps:

1. Make the environment with [uv](https://docs.astral.sh/uv/):

   ```bash
   uv venv --python 3.13 .venv
   uv pip sync --python .venv requirements-dev.txt
   ```

2. Get the data of the organizer:

   ```bash
   git clone https://github.com/Urzad-Zamowien-Publicznych/hacknation-2026.git data/uzp
   ```

3. Run the tests and the evaluation:

   ```bash
   .venv/bin/python -m pytest
   PYTHONPATH=src .venv/bin/python -m odw2json.evaluate --split dev --errors
   ```

The documentation is in `docs/`. The slides are in [`docs/presentation/CombAIns.pdf`](docs/presentation/CombAIns.pdf).

## License

[MIT](LICENSE)
