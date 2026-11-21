# CombAIns: Odwołania2json

A solution for the challenge "Odwołania2json" of HackNation 2026. The application reads the PDF documents of a KIO appeal case and writes one JSON file for each document.

The application uses rules, not an LLM. It finds the type of each document and extracts the data with rules from the configuration in `config/types/`. A document of an unknown type gives `{}`.

A page without a text layer (a scan) goes to OCR with RapidOCR. RapidOCR installs with `pip` and has its model files in the package, so no other program and no internet connection are necessary.

## Install

To install the application, do these steps:

1. Install Python 3.13 or a newer version.
2. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

For development, use the procedure in `CLAUDE.md`, section "Environment".

## Run

To process the documents, do these steps:

1. Put the PDF files into `input/<case>/`.
2. Start the application:

   ```bash
   python main.py
   ```

   On Windows, you can also start `start.bat`. On Linux, you can start `./start.sh`.

3. Read the JSON files in `output/<case>/`. Each JSON file has the name of its PDF file.

Use `--input` and `--output` to select other folders. Use `--workers` to set the number of processes.

## Web interface

To see a document and its data side by side, do these steps:

1. Start the web interface:

   ```bash
   python main.py --gui
   ```

2. Open http://127.0.0.1:8000 in a browser.
3. Select one or more PDF files.

The page shows the source text of each value. You can correct a value and download the JSON file.

## Measure the quality

The data of the organizer must be in `data/uzp/` (see `CLAUDE.md`, section "Data").

```bash
PYTHONPATH=src python -m odw2json.evaluate --split dev --errors
PYTHONPATH=src python -m odw2json.perturb --split dev
```

The first command gives the F1 score with the rules of the organizer. The second command changes the form of the text and measures the F1 score again.
