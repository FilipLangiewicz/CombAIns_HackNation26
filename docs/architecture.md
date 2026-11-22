# Architecture

This file tells how the parts of the application operate together. The details of each step are in other files:

- `docs/ocr-decision.md`: the decision about OCR.
- `docs/classification.md`: the type of the document.
- `docs/extraction-rules.md`: the rules for each type.
- `docs/new-document-type.md`: a new type from the configuration only.

## The flow of one document

```
PDF file
  │
  ▼
pdftext.read_pdf ──► text layer of each page (pypdfium2)
  │                  a page with fewer than 30 characters ──► OCR (RapidOCR, see docs/ocr-decision.md)
  ▼
classify.classify ──► scores of the types from config/types/*.yaml
  │                   no type with its minimum score ──► {} (unknown type)
  ▼
extractors.extract ──► the extractor of the type (odwolanie, pelnomocnictwo, przelew or generic)
  │                    then the field rules of the configuration
  ▼
validate.apply ──► the checks of the key "validate": a value that is not valid becomes null
  ▼
Result: type, data (the output JSON), evidence (the source text of each value), scores
  │
  ├──► cli.py: output/<case>/<file>.json
  └──► gui.py: the web page with the PDF and the fields side by side
```

## Files

| File | Purpose |
|---|---|
| `main.py` | The start of the application. It adds `src/` to the path and calls `cli.main`. |
| `src/odw2json/cli.py` | The command line: `input/` to `output/`, or `--gui`. |
| `src/odw2json/pipeline.py` | `process_pdf` and `process_text`: the flow above. |
| `src/odw2json/pdftext.py` | The text of the PDF and the decision about OCR. |
| `src/odw2json/ocr.py` | The OCR: rotation, text boxes, lines and columns, repair of OCR errors. |
| `src/odw2json/validate.py` | The validation of the fields from the key `validate` of a type. |
| `src/odw2json/classify.py` | The type files and the scores of the types. |
| `src/odw2json/common.py` | Shared rules: dates, amounts, accounts, identifiers, names. |
| `src/odw2json/extractors/` | One extractor for each known type, and `generic.py` for a type from the configuration. |
| `src/odw2json/gui.py`, `static/index.html` | The web interface. It uses only the Python standard library. |
| `src/odw2json/static/graph.html` | The pages `/graph` (the path of a document) and `/rules` (all rules). The data comes from `/api/pipeline`, which reads `config/types/*.yaml`. |
| `src/odw2json/evaluate.py` | The F1 score with the rules of the organizer. |
| `src/odw2json/perturb.py` | The robustness test: changed copies of the examples. |
| `src/odw2json/synth.py` | Generator 1 of new layouts. The rules were tuned on seeds 1 and 2. |
| `src/odw2json/synth2.py` | Generator 2 of new layouts, made without knowledge of the rules. It is a final test only. |
| `src/odw2json/scans.py` | The data set of synthetic and real scans for the OCR path, and its F1 report. |
| `jobs/` | The Kaggle jobs that make the OCR boxes of the scan data set (see `jobs/JOBS.md`). |
| `config/types/*.yaml` | One file for each document type: classification rules, template, labels, field rules. |
| `config/split.json` | The fixed split of the example cases into dev and holdout. |
| `config/names.yaml` | Polish first names for the conversion of names to the nominative. |
| `config/ocr_words.txt` | Polish words with diacritics for the repair of the OCR text. |

## Principles

- **No LLM.** The rules run on a laptop without a GPU in less than 0.1 s for each document with a text layer. A scan needs about 11 s for the OCR. No data goes to an external service. A solution without an LLM gets the maximum points for the size of the model.
- **Configuration, not code.** The words, labels and codes are in YAML files. A new type needs only a new YAML file.
- **Transparency.** Each value has its source text (evidence). The web interface shows it.
- **Safe failure.** If a rule finds no value, the value is `null`. If no type fits, the output is `{}`. An error in one file does not stop the other files.

## Run

- CLI: `python main.py` (or `start.bat`, `./start.sh`).
- Web interface: `python main.py --gui`, then open http://127.0.0.1:8000.
- Docker: `docker compose up` starts the web interface. `docker compose run --rm cli` processes the `input/` folder.

## Quality

| Command | Measurement |
|---|---|
| `PYTHONPATH=src python -m odw2json.evaluate --split dev` | F1 on the example cases of the organizer |
| `PYTHONPATH=src python -m odw2json.perturb --split dev` | F1 on changed copies of the examples |
| `PYTHONPATH=src python -m odw2json.synth --n 20` | F1 on new layouts (generator 1) |
| `PYTHONPATH=src python -m odw2json.synth2 --n 20` | F1 on new layouts (generator 2, final test) |
| `PYTHONPATH=src python -m odw2json.scans --report jobs/runs/*/output/*/ocr-shard-*.jsonl` | F1 of the OCR path for each split |
| `python -m pytest` | Unit tests |

The results of each run are in `docs/WORKLOG.md`.
