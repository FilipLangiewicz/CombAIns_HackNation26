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

If a document is not of a known type, the application writes an empty JSON file.

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

## Open questions

- Which LLM and which API provider in the EU do we use?
- How does the jury calculate F1: for each field, for each document, or for each case?
- How do we read scanned PDF files (OCR)?

## Plan

The team writes the plan here when it decides the architecture.
