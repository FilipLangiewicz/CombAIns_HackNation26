# Project plan

This file has the facts about the challenge and the plan of the team. The original materials are in `docs/task/`. The README and the JSON structures of the organizer are in `docs/task/organizer/`.

## The challenge

The input is a folder of PDF documents for each appeal case. The application does these steps for each document:

1. It reads the text of the PDF. Some PDF files are scans.
2. It finds the type of the document from its content, not from the file name.
3. It extracts the data that this type of document must have.
4. It writes one JSON file with the structure from `oczekiwane-json/`.

The known types of documents:

| Type | JSON structure |
|---|---|
| Appeal (`odwolanie`) | `oczekiwane-json/odwolanie.json` |
| Power of attorney (`pelnomocnictwo`) | `oczekiwane-json/pelnomocnictwo.json` |
| Payment confirmation (`przelew`) | `oczekiwane-json/przelew.json` |

If a document is not of a known type, the application writes a JSON file with only `{}`. The file has the name of the PDF file.

## Input and output

- The application has the folders `input/` and `output/` in its root folder.
- `input/<case>/<file>.pdf` gives `output/<case>/<file>.json`. The JSON file has the same name as the PDF file.
- The application starts from a CLI or from a wrapper script (for example `start.bat`). A GUI gives more points, but it is not necessary.

## Technical requirements

- Python 3.13 or a newer version.
- A `requirements.txt` file for `pip install`.
- Only open-source components, also the LLM.
- The application runs on a laptop without a GPU (16 GB RAM, Intel i7). The LLM runs through an API.
- The organizer gets the API key with the solution.
- The API provider must process the data on servers in the EU or the EEA. Its privacy policy must tell what the provider does with the data and where.

## Evaluation

Stage 1 (preselection): 100% F1 score on a hidden test set with at least 10 real cases.

Stage 2 (final, maximum three teams):

- 50%: F1 score on the hidden test set.
- 50%: flexibility of the solution:
  - 1-20 points: size of the LLM. A smaller model gets more points.
  - 1-20 points: a new type of document or a new data class without a rebuild of the system.
  - 1-10 points: other useful functions, for example a GUI.

The jury also gives points for transparency of the extraction.

## Deliverables

- The title of the project.
- A link to the GitHub repository of a prototype that operates.
- Optional: technical documentation (with the description of the LLM) and the results of our own quality tests.

If the team wins, it must also give these items:

- the source code and the instructions to run it
- a Docker Compose configuration
- documentation of the architecture
- documentation of the configuration of a document type
- documentation of the procedure to add a new document type

## Answers of the organizer (Discord, 2026-11-21)

The organizer gave these answers on the Discord channel of the challenge. They have priority over the PDF files in `docs/task/`.

The F1 score:

- True positive: the value is in our JSON and agrees with the reference.
- True negative: the value is not in our JSON and not in the reference.
- False positive: the value is only in our JSON, or the value is in both but it is not correct.
- False negative: the value is only in the reference.
- These fields are "long strings". For them, an 80% agreement is sufficient:
  - the name of the company of the attorney
  - the title of the payment
  - the name of the appellant and the name of the contracting authority
  - the title of the public procurement
- All other fields must agree exactly (for example KRS, NIP, dates, amounts).
- The jury matches the items of a list by their content, not by their order.

The data and the output:

- The 60 example cases in the organizer repository are the correct data. The presentation tells about 39 cases and `ground_truth.yaml`. This information is old.
- The test set has synthetic documents. The organizer made them from real cases.
- The folder `dane/skany/` has scans without a text layer: 10 appeals, 10 powers of attorney and 10 payment confirmations, each with its JSON. Thus the application must have OCR.
- The JSON must agree strictly with the format. Do not add fields, for example a quote of the source.
- Write the names of persons in the nominative case, for example "Mateusz Szymański", not "Mateusza Szymańskiego".
- In `czynnosc_opis`, use the text from `oczekiwane-json/czynnosc_powod_id_dict.md` exactly, for example "Odpowiedzi/wyjaśnienia do SWZ". The code 12 occurs only in this dictionary, not in the examples.

The LLM and the test machine:

- The LLM must be open source.
- A company must host the LLM in the EU. Its privacy policy must tell the scope and the place of the data processing.
- Do not host the LLM on a private computer. The organizer does not allow this.
- We give the API key to the organizer for the test.
- A solution without an LLM gets the maximum points for the size of the model.
- The test machine is a usual laptop with internet. There is no time limit.
- If the repository is private, give access to these GitHub accounts: `DominikOlczak`, `MateuSzSz-Sz`, `rkrol-dev`.

## Answers of the organizer (Discord, 2026-11-21, evening)

- A bank account must be written as the document gives it. An example JSON without "PL" for a document with "PL" is an error of the examples. The evaluation set does not have this error. The application writes "PL" and 26 digits without spaces if the document has "PL".
- The name of a company must be written as the document gives it, also if it differs from CEIDG.
- A document of an unknown type gives a JSON file with only `{}`. The JSON file has the name of the PDF file, for example `potwierdzenie_przelewu.json`.
- The evaluation uses documents with a text layer and scans.
- A new document type must be possible with a configuration file only.
- A small NER model (not an LLM) that runs locally is allowed.
- The number of documents and the time limit are not known yet. One team mentioned 150 documents in 45 minutes.

## FAQ of the organizer (version 1.0)

These points of the FAQ add to the information above:

- If a document does not have a value, do not invent it. Use `null` where the structure allows it, as the examples show.
- The application must read PDF files with a text layer and scans (OCR).
- The LLM must be free of license fees. It must also be possible to install it locally.
- A CLI with instructions is necessary. It is the most important interface.
- A GUI is optional, but it gives points. The ideal GUI has these functions:
  - upload a PDF file
  - start the analysis
  - show the source document and the extracted data side by side
- The final evaluation gives many points when a new type or a new field needs only a change of the configuration.
- The UZP stand at the event shows examples of the test data.

## Decisions

- No LLM. The rules give the results below. A solution without an LLM gets the maximum points for the size of the model.
- OCR: RapidOCR (PP-OCRv6). It installs with pip only and has its models in the package. Details in `docs/ocr-decision.md`.
- The API key: not necessary, because the application uses no external service.

## Notes about the data

- The JSON files in `oczekiwane-json/` have comments (`//`). A usual JSON parser cannot read them. Use `json5` or remove the comments.
- Some titles have spaces between the letters, for example "P E Ł N O M O C N I C T W O".
- A payment confirmation often has the data in a table with labels and values.
- Many values have a fixed form (NIP, REGON, KRS, PESEL, IBAN, amounts, dates). Rules can find them without an LLM.

## Plan

The first version is in `main`. The complete description of the parts is in `docs/architecture.md`.

### Architecture

The application uses rules, not an LLM. A solution without an LLM gets the maximum points for the size of the model.

1. `pdftext.py` reads the text layer with pypdfium2. A page with fewer than 30 characters goes to OCR (`ocr.py`, RapidOCR).
2. `classify.py` gives a score to each type with weighted regular expressions from `config/types/*.yaml`. If no type has its minimum score, the output is `{}`.
3. An extractor for each type finds the values. Each extractor also records the source text of each value (evidence).
4. `extractors/generic.py` reads field rules from the configuration. Thus a new type or a new field needs only a YAML file.
5. `validate.py` checks the values with the key `validate` of the type.
6. `cli.py` writes `output/<case>/<file>.json`. `gui.py` shows the PDF and the fields side by side.

### Measurement

- `python -m odw2json.evaluate --split dev` gives the F1 score with the rules of the organizer. The tests in `tests/test_evaluate.py` check the score on cases with known results.
- `python -m odw2json.perturb --split dev` changes the form of the text and keeps the expected values. It shows the rules that fail on other layouts.

### Status (2026-11-22, morning)

The work is in `main`. The results are in `docs/WORKLOG.md`. The last measurement on the test split:

| Path | Test set | F1 |
|---|---|---|
| text | organizer holdout cases | 1.000 |
| text | generator 2 (new layouts), seeds 1, 7, 101 | odwolanie 0.99, pelnomocnictwo 1.00, przelew 1.00 |
| OCR | test split, all | 0.955 |
| OCR | real scans 0005-0010 (test split) | 0.892 |

The web interface has the pages `/graph` (the path of a document) and `/rules` (all rules of each type).

### Next steps

Do the work on a new branch. Merge it into `main` when the tests and the measurements are good. In the order of the value:

1. The appeal with a new layout: the block of the appellant and the attorney. Tune on generator 1 (`odw2json.synth`, seeds 1 to 3) and on the OCR train split. Measure on generator 2 and on the OCR test split only at the end.
2. The real scans: the reading order of tables with three columns in bank confirmations (`ocr.boxes_to_lines`), and the OCR errors in names.
3. The speed, if the organizer gives a time limit: `ODW2JSON_OCR_MAX_PAGES`, `--workers`.
4. A new OCR data set on Kaggle after each change of the OCR steps (`jobs/new_ocr_jobs.py`). A change of the rules only needs `odw2json.scans --report` on the boxes that are in `jobs/runs/`.

### How to continue the work

1. Clone the data of the organizer into `data/uzp/` (see `CLAUDE.md`, section "Data").
2. Run `uv pip sync --python .venv requirements-dev.txt`. The lock has RapidOCR now.
3. Run the tests and the measurements in `docs/architecture.md`, section "Quality". The OCR boxes of the scan data set are in `jobs/runs/*_ocr-set-v5*/output/`.
4. Do not tune rules on the test split: the organizer holdout cases, generator 2, and the real scans 0005-0010.
