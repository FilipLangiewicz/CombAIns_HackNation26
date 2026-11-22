# Worklog

Add new entries at the top. Each entry has the date, the branch and the changes.

## 2026-11-22 (main): e-mail addresses and signers after OCR errors

The errors come from the OCR train split.

- `ocr.repair_emails`: the OCR can put a space before the top domain: "biuro@firma .example". The repair also removes Polish letters from an address, because the repair of the diacritics can add them.
- `pelnomocnictwo.find_signers`: a line "miejsce na pieczęć firmowa" between the name and the role is not a part of the signature. The text "miejsce na pieczęć firmowa" before the names is removed. A dot "·" before a role is removed.
- `pelnomocnictwo.find_company_name`: a stop word with OCR errors ("MOCODAWCA·", "Pehnomocnictwo") also stops the name.
- Three new tests.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1 and 2 | no change | no change |
| OCR train / val | 0.9852 / 0.9797 | 0.9873 / 0.9797 |

## 2026-11-22 (main): final check of the changes of this night

- `pelnomocnictwo.find_company_name`: a stop word that the OCR split ("PELNOMOCNI CTWO") also stops the name.
- The final check on the test split showed this error. The legal form "Sp. z o.o." matches since commit `2946d08`, so the split title came into the name. The fix is general, but it comes from a test document. Thus the test numbers below are a little optimistic.
- New test in `tests/test_pelnomocnictwo.py`.

The final check, one run on the test split:

| Test set | Before the night (`24d74bf`) | After |
|---|---|---|
| Generator 2, seeds 1 / 7 / 101, `odwolanie` | 0.927 / 0.932 / 0.918 | 0.989 / 0.990 / 0.991 |
| Generator 2, seeds 1 / 7 / 101, `pelnomocnictwo` | 0.994 / 0.986 / 0.984 | 1.000 / 1.000 / 1.000 |
| Generator 2, seeds 1 / 7 / 101, `przelew` | 0.967 / 0.987 / 0.982 | 1.000 / 1.000 / 1.000 |
| OCR test, all | 0.9369 | 0.9552 |
| OCR test, real scans 0005-0010 | 0.8889 | 0.8921 |
| OCR train / val | 0.9849 / 0.9783 | 0.9852 / 0.9797 |
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |

## 2026-11-22 (main): the pages /graph and /rules in the web interface

- New file `src/odw2json/static/graph.html`: an interactive graph of the path of a document, and a page with all rules of each type.
- `/graph`: the nodes are the PDF file, the decision "text layer or OCR", the classification, each type and the unknown type, the extraction, the validation and the JSON file.
- For an analysed document, `/graph` marks its path and gives the reason of each decision. Examples: the points of each type, the rules that matched, the OCR pages.
- `/rules`: the classification rules, the rules of the contested action, the validation, the other parameters and the full YAML file of each type.
- `gui.pipeline_info` and `/api/pipeline` read `config/types/*.yaml` and the constants of `pdftext`. Thus the pages have no copy of the rules.
- `pipeline.Result` has the number of pages and the skipped pages. The web interface also gives the validation warnings.
- New test in `tests/test_evidence.py`.

## 2026-11-22 (main): the name of the principal in a power of attorney

- `config/types/pelnomocnictwo.yaml`: the legal forms "sp. z o.o.", "sp. k." and "sp. k.a." match without regard to the case. Before, "Sp. z o.o." did not match.
- `pelnomocnictwo.find_name_without_legal_form`: the anchor "Mocodawca" stays on its line, and can have a number: "Mocodawca 1:". A heading "§ 1. Mocodawca" is not a part of the name below it.
- Two new tests in `tests/test_pelnomocnictwo.py`.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1, seeds 1 to 3 | no change | no change |
| Generator 2, `pelnomocnictwo`, seeds 55 / 56 / 57 | 0.970 / 0.984 / 0.974 | 0.992 / 0.999 / 0.989 |
| OCR train / val | 0.9852 / 0.9797 | 0.9852 / 0.9797 |

## 2026-11-22 (main): a title in more lines in the table of a bank confirmation

- `przelew.merge_columns`: in a table with all labels first and then all values, the title can take more lines. The labels after the title select the number of lines: an amount, a date and a transaction number must have their form.
- New test in `tests/test_przelew.py`.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1, seeds 1 to 3 | no change | no change |
| Generator 2, `przelew`, seeds 55 / 56 / 57 | 0.977 / 0.991 / 0.979 | 1.000 / 1.000 / 1.000 |
| OCR train / val | 0.9852 / 0.9797 | 0.9852 / 0.9797 |

## 2026-11-22 (main): joint authorities, a second attorney and the letterhead of the law firm

The errors come from generator 2 with the seeds 55 to 57. The fixes are in `extractors/odwolanie.py`.

- "w imieniu pozostałych" in the role of an authority is not the start of the appellant.
- A role after identifiers in parentheses, "(NIP: ...) – prowadzący postępowanie;", belongs to the authority before it.
- "r. pr. Anna Nowak, adw. Jan Kos Kancelaria ...": the second attorney is not a part of the name of the law firm.
- The title "Odwołanie" before the town is not a part of the town.
- If the appeal has no law firm near the attorney, the letterhead above the town and the date gives the firm and the e-mail.
- Five new tests in `tests/test_odwolanie.py`.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1, seeds 1 to 3 | no change | no change |
| Generator 2, `odwolanie`, seeds 55 / 56 / 57 | 0.981 / 0.956 / 0.978 | 0.995 / 0.991 / 0.987 |
| OCR train / val | 0.9852 / 0.9797 | 0.9852 / 0.9797 |

## 2026-11-22 (main): party tables and more forms of the contested action

The errors come from generator 2 with the new seeds 55 to 57. The final test seeds 1, 7 and 101 stay for the final check.

- `odwolanie.unfold_tables`: a party table gives the labels ("Nazwa", "Adres", "KRS") in lines and then the values. Now each value gets its label. A value "-" is empty.
- The name of the attorney does not take a label of the next line: "Katarzyna Michalak Kontakt:".
- `config/types/odwolanie.yaml`, `action_rules`:
  - "niewykluczeniu", "niedokonaniu odrzucenia" and "nieunieważnieniu" are omissions (codes 8, 7, 10).
  - "zmiana SWZ" is a modification of the SWZ (code 5).
  - "wzór umowy" at the start of an item is code 12. In a list after "SWZ w zakresie", it is a part of the SWZ (code 4).
- Seven new tests in `tests/test_odwolanie.py`.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1, seeds 1 to 3 | no change | no change |
| Generator 2, `odwolanie`, seeds 55 / 56 / 57 | 0.941 / 0.917 / 0.938 | 0.981 / 0.956 / 0.978 |
| OCR train / val | 0.9849 / 0.9783 | 0.9852 / 0.9797 |

## 2026-11-22 (main): the title of the procurement after OCR errors

The OCR loses quote marks and spaces near the title, and can change the label. The fixes are in `odwolanie.parse_procurement`.

- The first quote mark is optional after a label and after "Postępowanie": 'Postępowanie Odbiór odpadów" (ZP/101/2026)'.
- "Przedmiot Odwołanie:" is a label, the same as "Przedmiot odwołania:".
- "Postępowanie nr PN/244/2026:" is a label.
- After the last quote mark, "nr" can follow without a space or after a stray mark: `biurowych"'nr referencyjny`.
- Five new tests in `tests/test_odwolanie.py`. Three of them fail with the old code.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text), generator 1 and 2 | no change | no change |
| OCR train | 0.9838 | 0.9849 |
| OCR val | 0.9742 | 0.9783 |
| OCR test (final check) | 0.9369 | 0.9369 |

## 2026-11-22 (main): the signer of a power of attorney in two OCR columns

The OCR can mix the rows of two signature columns. Then the role of the signer ("Prezes Zarządu") stands under the name of the attorney. The extractor took the attorney as the signer.

- `pelnomocnictwo.find_signers`: a name with a professional title before it (`titles` in the config) is not a signer.
- A name under the heading "Mocodawca:" or "Za Mocodawcę:" is a signer.
- New test in `tests/test_pelnomocnictwo.py`. It fails with the old code.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1 and 2, `pelnomocnictwo` | no change | no change |
| OCR train, `pelnomocnictwo` | 0.9728 | 0.9781 |
| OCR train / val | 0.9826 / 0.9742 | 0.9838 / 0.9742 |
| OCR test, `pelnomocnictwo` (final check) | 0.9437 | 0.9464 |

## 2026-11-22 (main): more forms of the authorities and of the law firm in the appeal

New probe texts showed these errors. The fixes are in `extractors/odwolanie.py`. Eight new tests in `tests/test_odwolanie.py` fail with the old code.

- A list mark before the name of a party ("1.", "a)", "-", "oraz") is not a part of the name.
- New role tags after a dash: "– Lider Zamawiających", "– Zamawiający prowadzący postępowanie", "– pełnomocnik Zamawiających prowadzący postępowanie".
- The sentence "Postępowanie prowadzi Gmina Alfa." marks the lead authority.
- The name of a law firm does not take the address of the next line.
- The surnames of the partners before "Kancelaria" are not a part of the name of the attorney.
- "z Kancelarii ..." gives the firm in the nominative: "Kancelaria ...".

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1, seeds 1 to 3, `odwolanie` | 1.000 / 0.999 / 0.992 | 1.000 / 0.999 / 0.992 |
| OCR train / val | 0.9826 / 0.9735 | 0.9826 / 0.9742 |
| Generator 2, `odwolanie`, seeds 1, 7, 101 (final test) | 0.927 / 0.932 / 0.918 | 0.927 / 0.932 / 0.918 |

Generator 2 does not change. Its errors come from other layouts than the probe texts.

## 2026-11-22 (main): tables with a label and a value in the OCR text

- `ocr.boxes_to_lines`: two or more rows with two parts are two columns, for example two signature blocks. Now a table with a label without digits at the left and a value with digits at the right stays in rows. Bank confirmations have such tables.
- New test in `tests/test_ocr.py`. It fails with the old code.
- The OCR cache keeps the boxes, not the lines. Thus `OCR_VERSION` stays 5.

| Test set | Before | After |
|---|---|---|
| Organizer dev (text) | 1.000 | 1.000 |
| OCR train | 0.9815 | 0.9826 |
| OCR train, `przelew` | 0.9843 | 0.9903 |
| OCR val | 0.9735 | 0.9735 |
| OCR test (final check) | 0.9363 | 0.9363 |

## 2026-11-22 (main): tests for the classification of similar documents

- New file `tests/test_classify.py`: 20 short texts that look like an appeal, a power of attorney or a bank confirmation, but are of no known type. Also 6 known documents in other forms.
- `config/types/odwolanie.yaml`: two new rules. A title in a sentence ("Odwołanie od czynności ...") and "wnoszę odwołanie" count for an appeal.
- Before the change, an appeal with the title in a sentence had no type.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| 12 negative documents of the organizer | 0 with a type | 0 with a type |
| Generator 1, seeds 1 to 3 | no change | no change |
| OCR report, all splits | no change | no change |
| Generator 2, seed 1, `odwolanie` | 0.927 | 0.927 |

## 2026-11-22 (main): the deployment on the VM

- New file `docs/deployment.md`: the rules of the organizer, the VM, the update procedure and the test results.
- `README.md`: a link to `RUN.md` and `docs/deployment.md`.
- Commit `1ae7827` is on the VM in `/opt/solution`, with the Docker image `solution-cli`.
- All 226 PDF files of the organizer and 6 broken files ran on the VM in 434 s, with exit code 0.

## 2026-11-22 (main): the run on the VM of the organizer

- `RUN.md`: the command for the jury, `docker compose run --rm cli`. The organizer runs it in `/opt/solution` on an Ubuntu VM.
- `Dockerfile`: the build downloads the RapidOCR models. Without this step, the first OCR needs the internet.
- A test with `docker run --network none` on example case 01, three real scans and one negative document gave correct results.

## 2026-11-22 (main): repairs for the OCR path

- `pelnomocnictwo`: a list of names after "udziela Pełnomocnictwo:" gives the attorneys. A title in parentheses after the name also marks an attorney.
- `pelnomocnictwo`: the full legal forms, for example "Spółka z ograniczoną odpowiedzialnością".
- `pelnomocnictwo`: "przez: Jan Nowak - Wiceprezes Zarządu" gives a signer also across a line break.
- `przelew`: a date in the next line of a table is not an amount.
- `przelew`: "20260715/3219039" is not a page number.
- `przelew`: an account can have a dot or other separators from the OCR.
- `przelew`: a damaged account near to a known account (`known_accounts`, the UZP account) becomes this account.

| Test set | Before | After |
|---|---|---|
| Organizer dev and holdout (text) | 1.000 | 1.000 |
| OCR train / val | 0.980 / 0.963 | 0.982 / 0.974 |
| OCR val, real scans 0001-0004 | 0.935 | 0.979 |
| OCR test, all / real scans 0005-0010 (one run) | 0.933 / 0.866 | 0.936 / 0.889 |
| Generator 2, seeds 1, 7, 101 (one run) | no change | no change |

## 2026-11-22 (main): the headings of the parties and the signature of the attorney

Generator 2 did not find the appellant in 8 of 20 appeals. Only the summary of the fields was read, not the documents. The rules below come from new probe texts.

- A heading of a party on its own line, without a colon, is a heading: "ODWOŁUJĄCY", "I. Odwołujący", "Odwołujący –".
- "Zamawiający 1 (...):" and "Odwołujący 1:" are headings.
- If no heading "Odwołujący" is found, "Wykonawca:" is the heading of the appellant.
- The identifiers can have "nr", "numer", "PL" and ";". A list number "2)" is not a part of an identifier.
- New words for the field `prowadzacy_postepowanie`: "pełnomocnik Zamawiających", "wiodący", "koordynator", "upoważniony".
- A name of an attorney does not take the first word of the next line.
- If the header has no attorney, a name with a professional title in the signature is the attorney. All 45 dev appeals have such a signature.

| Test set | Before | After |
|---|---|---|
| Organizer dev and holdout (text) | 1.000 | 1.000 |
| Generator 1, seeds 1 to 3, `odwolanie` | 0.995-0.997 | 0.995-0.997 |
| OCR train / val | 0.980 / 0.963 | 0.980 / 0.963 |
| Generator 2, `odwolanie`, seeds 1, 7, 101 (final test) | 0.832 / 0.844 / 0.834 | 0.927 / 0.932 / 0.918 |
| Generator 2, `przelew`, seeds 1, 7, 101 | - | 0.967 / 0.987 / 0.982 |
| OCR test, all / real scans 0005-0010 | 0.907 / 0.862 | 0.933 / 0.866 |

## 2026-11-22 (main): the appellant and the attorney in the appeal

- "reprezentowana przez Prezesa Zarządu ..." names a member of the board, not an attorney. Then `przez-pelnomocnika` is 0. The roles are in `board_roles` of `config/types/odwolanie.yaml`.
- "reprezentowana przez pełnomocnika: r. pr. ..." gives the name of the attorney.
- The block "Pełnomocnik Odwołującego: ..." can stand before the appellant.
- A sole trader gives the name after "pod firmą".
- The name of a law firm keeps the surnames before "Kancelaria". An e-mail domain or an address is not a law firm.
- A number of the form `NNNNNN-YYYY` without a label is the TED number.
- Generator 1: the layout `od_4` now shows the TED number that is in its gold JSON.

F1 of `odwolanie`, no LLM:

| Test set | Before | After |
|---|---|---|
| Generator 1, seeds 1 to 3 (42 documents) | 0.988-0.990 | 0.995-0.997 |
| Organizer dev and holdout (text) | 1.000 | 1.000 |
| OCR train / val | 0.983 / 0.965 | 0.984 / 0.977 |
| OCR, all splits: val real scans | 0.916 | 0.935 |
| Generator 2, seeds 1, 7, 101 (final test, one run) | 0.832 / 0.843 / 0.834 | 0.832 / 0.844 / 0.834 |
| OCR test, real scans 0005-0010 (one run) | 0.845 | 0.862 |

Generator 2 does not change. Its errors are of other kinds than the role of the attorney.

## 2026-11-22 (main): the roles in the power of attorney

The organizers told many times that a system can confuse the attorney and the signer. This work makes the roles come from the words near the name.

- Generator 1 has five new layouts of `pelnomocnictwo` (`pl_10` to `pl_14`):
  - the attorney accepts the power under the signature of the principal;
  - a letterhead of the law firm with its own NIP;
  - "Pan" and "Pani" without a professional title for the signer and for the attorney;
  - a table with two columns;
  - roles and names in the accusative: "przez Prokurenta Katarzynę Nowak".
- New rules in `extractors/pelnomocnictwo.py` and in `config/types/pelnomocnictwo.yaml`:
  - A name found only by "Pan" or "Pani" is not an attorney if this person signs.
  - A professional title after the name also marks an attorney.
  - The prose can name a signer: "Jan Nowak (Prezes Zarządu)" or a role before the name (`roles_before_name`).
  - A company with a word of a law firm (`law_firm_words`) is not a principal.
  - A legal form between two identifiers starts a new company.

F1 of `pelnomocnictwo`, no LLM:

| Test set | Before | After |
|---|---|---|
| Generator 1 with the new layouts, seeds 1 to 5 (42 documents) | 0.928-0.949 | 0.990-1.000 |
| Organizer dev and holdout (text) | 1.000 | 1.000 |
| OCR train / val | 0.971 / 0.937 | 0.972 / 0.937 |
| Generator 2, seeds 1, 7, 101 (final test, one run) | 0.988 / 0.974 / 0.984 | 0.994 / 0.986 / 0.984 |

## 2026-11-21, evening (rule-pipeline): the OCR path

- OCR with RapidOCR (PP-OCRv6, pip only). Details in `docs/ocr-decision.md`.
- A data set of 862 documents for the OCR path (`odw2json.scans`): synthetic scans of the organizer documents and of both generators, and the 30 real scans. The split has no leakage: train, val and test come from different cases and sources.
- The OCR runs on Kaggle: 15 CPU sessions on three accounts (`jobs/new_ocr_jobs.py`). The outputs are the OCR boxes, so the rules for lines change without a new OCR.
- New validation of fields in the type configuration (`validate`), and the OCR reads all pages only when the type needs them.

F1 of the OCR path, no LLM (the text path stays at 1.0 on the organizer examples):

| Step | Commit | train | val | real scans in val |
|---|---|---|---|---|
| OCR without repairs (v1) | 6cd94d5 | 0.74 | - | - |
| diacritics, folded classification | a4576ff | 0.91 | - | - |
| fonts, boxes, columns (v2) | 1ddbfd4 | 0.94 | - | - |
| split of long boxes before the recognition (v4) | 90c8979 | 0.959 | - | - |
| fuzzy titles, e-mails, letter errors (v5) | 94ab339 | 0.978 | 0.944 | 0.838 |
| first action after "wnoszę odwołanie wobec" | ce790c2 | 0.978 | 0.952 | 0.891 |
| more repairs for the real scans | 27a2c25 | 0.979 | 0.953 | 0.916 |

Final measurement on the test split (no rule was tuned on it), commit ffc53cb:

| Path | Test set | F1 |
|---|---|---|
| text | organizer holdout cases | 1.000 |
| text | generator 2, seeds 1, 7 and 101 | odwolanie 0.83-0.84, pelnomocnictwo 0.97-0.99, przelew 0.97-0.99 |
| OCR | organizer holdout cases as scans | 0.989 |
| OCR | generator 2 as scans | 0.871 |
| OCR | real scans 0005-0010 | 0.845 |
| OCR | all | 0.907 |

The real scans give 0.916 in val and 0.845 in test. Thus a part of the repairs fits the 12 real scans of val. The weakest type is the appeal with a new layout.

Run of the complete application (`python main.py`) on 226 files, commit c588dcb:

- The files are the 60 example cases, the 30 real scans and the 12 negative documents.
- 226 files took 630 s with 4 processes. No file gave an error.
- Organizer PDF files with a text layer: F1 1.000. Negative documents: all `{}`.
- All 30 real scans: F1 0.874.
- A clean installation with `pip install -r requirements.txt` and the Docker image both run the OCR.

- Time: 12 real scans took 250 s before the page limit and 135 s after it (about 11 s for each document, 8 cores).
- The organizer confirmed: a bank account as in the document, with the country code and without spaces.

## 2026-11-21 (rule-pipeline)

- Kaggle limits, measured: 5 CPU sessions at the same time for each account ("Maximum batch CPU session count of 5 reached"). With three accounts, 15 CPU sessions of 4 cores run at the same time.
- The GPU gave no speed for RapidOCR: onnxruntime-gpu found no CUDA device, so the OCR ran on the CPU. The OCR jobs use the CPU only.
- `jobs/new_ocr_jobs.py` makes the job folders for all accounts from `jobs/ocr_run_template.py`.

- Make the rules of the three types more general with the errors of `odw2json.synth` (seeds 1 and 2).
- Add `odw2json.synth2`: a second generator, written without knowledge of the rules and of the first generator. It is the final test. Do not tune the rules on it.
- Result after the work (F1, 20 documents for each type, no LLM):

| Test set | odwolanie | pelnomocnictwo | przelew | negative documents |
|---|---|---|---|---|
| Organizer examples (dev, holdout, negatywne) | 1.000 | 1.000 | 1.000 | all `{}` |
| synth, seed 1 (before the work) | 0.700 | 0.885 | 0.622 | 3 of 20 wrong |
| synth, seed 7 (after the work) | 0.980 | 0.991 | 0.996 | all `{}` |
| synth2, seed 1 (final test) | 0.832 | 0.984 | 0.967 | all `{}` |
| synth2, seed 7 (final test) | 0.843 | 0.974 | 0.987 | all `{}` |

- The classification is correct for all documents of synth2.
- The weak part is `odwolanie` on new layouts: the appellant block and the attorney (`Odwolujacy[]`, `pelnomocnik`). In synth2 the result of `odwolanie` changed only from 0.818 to 0.832 after the work. Thus a part of the work fits the first generator only.

- Add `odw2json.synth`: a generator of new layouts. It was written without knowledge of the rules, so it measures the fit to the examples.
- First result on new layouts (20 documents for each type, seed 1, commit 62dd835): przelew 0.62, pelnomocnictwo 0.88, odwolanie 0.70. Three of 20 negative documents ("Odpowiedź na odwołanie") were classified as odwolanie.
- Conclusion: the rules fit the layouts of the examples too closely. The next work makes the rules more general.

- Add the pipeline: text from the PDF, the classifier from `config/types/*.yaml`, one extractor for each type.
- Add the F1 evaluation with the rules of the organizer, and a fixed split in `config/split.json` (45 dev cases, 15 holdout cases).
- Add the robustness test `odw2json.perturb`.
- Add the web interface (`python main.py --gui`), `start.bat`, `start.sh`, and the `input/` and `output/` folders.

| Run | Commit | LLM | F1 dev | F1 holdout | Time for one document |
|---|---|---|---|---|---|
| Rules only, no OCR | 3c28e57 | none | 1.0000 | 1.0000 | 0.01 s |
| Rules after the robustness work | e97baf5 | none | 1.0000 | 1.0000 | 0.01 s |

The robustness test (all transforms together) gave 0.87 on dev before the robustness work. After it, the test gives 1.00 on dev and on holdout.

The scans are not in this result, because OCR is not available yet. The classification of the 16 negative documents is correct.

## 2026-11-21 (main)

- Rename `AGENTS.md` to `CLAUDE.md`. Claude Code reads this file automatically.

- Add the answers of the organizer from Discord and notes about the data to `docs/project.md`.
- Prepare the repository: `AGENTS.md`, `KAGGLE.md`, `.gitignore`, `README.md`, `docs/project.md` and the files of the environment.
- Add the materials of the challenge to `docs/task/`, with copies of the organizer README and of the JSON structures in `docs/task/organizer/`.
