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

## Open questions

- Which LLM and which API provider in the EU do we use?
- How do we give the API key to the organizer? Somebody asked this on Discord. There is no answer yet.
- Which OCR engine gives good results on the scans on a CPU?

## Notes about the data

- The JSON files in `oczekiwane-json/` have comments (`//`). A usual JSON parser cannot read them. Use `json5` or remove the comments.
- Some titles have spaces between the letters, for example "P E Ł N O M O C N I C T W O".
- A payment confirmation often has the data in a table with labels and values.
- Many values have a fixed form (NIP, REGON, KRS, PESEL, IBAN, amounts, dates). Rules can find them without an LLM.

## Plan

The team writes the plan here when it decides the architecture.
