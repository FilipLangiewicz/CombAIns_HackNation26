# Worklog

Add new entries at the top. Each entry has the date, the branch and the changes.

## 2026-11-22 (gui-fixes): remove a document from the history, a larger decision shape

- The list of documents on the pages `/` and `/graph` shows "×" on each document under the mouse. A click removes the document from the history.
- New request `DELETE /api/docs/<id>` in `gui.py`. It also deletes the PDF file from the temporary folder.
- The decision shape "Strona ma warstwę tekstową?" on the page `/graph` is larger (380 × 100). Before, it cut the text.

## 2026-11-22 (main): the name KIOsk

The team selected the name "KIOsk" for the solution.

- The pages `/`, `/graph` and `/rules` show "KIOsk" in the title and in the heading.
- The main page shows "Odwołania2json" as a part of the subtitle.
- The title of `README.md` is "KIOsk: Odwołania2json".
- The page `/graph` has no remarks about the organizer now.

## 2026-11-22 (probe-sweep): new layouts of the power of attorney and of the bank transfer

Five probe texts of the power of attorney and four probe texts of the bank transfer showed these errors.

- `pelnomocnictwo.find_person_principal`: a NIP, a REGON or "z siedzibą" can follow the firm of a sole trader. Before, the name of the firm was lost.
- `pelnomocnictwo.find_signers`: the role in another case can follow the name: "reprezentowana przez Piotra Zająca, Prezesa Zarządu".
- `common.parse_amount`: the English form "15,000.00" gave 15.0. Now it gives 15000.0.
- `przelew.unfold_header_rows`: a row of labels with a row of values below it. Before, the year of the date became the amount.
- `config/types/przelew.yaml`: the label "Opis transakcji" of the title.
- Three new tests.

The results do not change on any test set:

- organizer dev / holdout: 1.000 / 1.000
- OCR train / val / test: 0.9876 / 0.9818 / 0.9673
- the generators `synth` and `synth2`

## 2026-11-22 (probe-sweep): new layouts of the appeal

Eight probe texts with new layouts of the appeal showed these errors. The fixes are in `extractors/odwolanie.py`.

- The action only in the title sentence: "ODWOŁANIE od czynności ... polegającej na odrzuceniu oferty". `title_action` reads this sentence before the other rules.
- The date label "dn.": "Lublin, dn. 01.10.2026".
- The role "– lider postępowania" stayed in the name of the authority ("Zamawiający").
- A party in one line, with the identifiers in brackets: "Odwołujący: Firma S.A. (KRS ...)".
- The words "z siedzibą w ..." after a name do not go into the name.
- The identifiers with "|" between them: "NIP: ... | REGON: ... | KRS: ...".
- The labels "nr ref." and "znak:" of the procurement number.
- Four new tests in `tests/test_odwolanie.py`.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout | 1.000 / 1.000 | 1.000 / 1.000 |
| OCR train / val / test | 0.9874 / 0.9818 / 0.9673 | 0.9876 / 0.9818 / 0.9673 |
| Generators `synth` and `synth2` (seeds for the tune of rules) | no change | no change |

## 2026-11-22 (main): the attorney in the letterhead of the appeal

Probe texts with the attorney at the top of the appeal showed three errors. The fixes are in `extractors/odwolanie.py`.

- The signature: in a short appeal, the last 700 characters also have the letterhead. The code took the first title ("ADW. JAN NOWAK" in capitals) and found no name. Now the last title with a name is the signature.
- "Od: Kancelaria Prawna Lex sp.k." is the sender. It is the appellant only if the appeal has no section "Odwołujący". Before, the law firm became the appellant.
- A letterhead without the word "Kancelaria" gives the e-mail of the attorney only if it has the surname of the attorney. The letterhead of the appellant does not give an e-mail to the attorney.
- Four new tests in `tests/test_odwolanie.py`.

The clean test of the complete application (no OCR cache) on the VM and on the laptop gave the same results:

| Test set | Files | F1 |
|---|---|---|
| Organizer dev / holdout | 135 / 45 | 1.000 / 1.000 |
| Organizer negative files | 12 | 1.000 |
| Real scans val / test | 12 / 18 | 0.992 / 0.992 |
| All, on the VM with the command of `RUN.md` | 226 | 0.999, in 369 s |

After the fixes, the results do not change on any test set.

## 2026-11-22 (main): two OCR errors from the test of 300 DPI

The test of 300 DPI (entry below) did not change the layout of the pages. It gave other letter errors, and two rules were not robust:

- The town and the date without a space: "Białystok,10.04.2026 r.". `odwolanie.PLACE_DATE_RE` now accepts it.
- "t" for "ł": "odwotanie", "Odwotujący". `ocr.repair` repairs the words that start with "odwot", because no Polish word starts so.
- Two new tests.

| Variant on the 30 real scans and the 12 negative files | Before | After |
|---|---|---|
| Current: 200 DPI, second OCR with 300 DPI | 0.992 | 0.992 |
| 300 DPI for all scans | 0.977 | 0.989 |

The other test sets do not change: organizer dev / holdout 1.000, OCR train / val 0.9874 / 0.9818.

## 2026-11-22 (main): OCR with 300 DPI for all scans is worse

A test of the complete application on the 30 real scans and the 12 negative files, 4 processes:

| Variant | Real scans val | Real scans test | All |
|---|---|---|---|
| 200 DPI, a second OCR with 300 DPI for a weak result (current) | 0.992 | 0.992 | 0.992 |
| 300 DPI for all scans | 0.966 | 0.984 | 0.977 |

A higher resolution repairs some letters, but it changes the layout of other pages. Example: the appeal 0002 lost the date, the town and the contested action. Thus the current variant stays.

- The run at 300 DPI showed the title "PEŁNOMOCNICTWO" in three parts: "PELNO MOCNIC TWO". `pelnomocnictwo.find_company_name` now joins two or three parts of a stop word.
- New test in `tests/test_pelnomocnictwo.py`. The other results do not change.

## 2026-11-22 (main): a second OCR with 300 DPI for a weak result

The real scan 0009 (appeal) gave unreadable text at 200 DPI. At 300 DPI, the OCR read it almost without errors. The OCR at 300 DPI is slower, so the pipeline uses it only for a weak result.

- `pipeline.weak`: a scan is weak if it has no type, or if a field of the key `ocr_retry_if_empty` of its type is empty.
- A document without a type gets the second OCR only if one type has at least half of its minimum score. A negative document is far below each minimum score.
- `pipeline.process_pdf`: the second OCR fills only the empty fields. It does not change a value of the first OCR.
- `config/types/*.yaml`: new key `ocr_retry_if_empty`. `numer_transakcji` is not in the list, because many confirmations have no transaction number.
- `ocr.DPI` and `ocr.RETRY_DPI` come from the environment variables `ODW2JSON_OCR_DPI` (200) and `ODW2JSON_OCR_RETRY_DPI` (300).
- The page `/graph` shows the second OCR.
- `odwolanie.parse_procurement`: the OCR can read the first quote mark of the title as a comma, and a semicolon can follow the last quote mark. The real scan 0003 (val split) showed this error.
- New tests in `tests/test_evidence.py` and `tests/test_odwolanie.py`.

The complete application on the 30 real scans and the 12 negative files, 4 processes:

| Test set | 200 DPI only | With the second OCR |
|---|---|---|
| Real scans 0001-0004 (val) | 0.992 | 0.992 |
| Real scans 0005-0010 (test, not independent now) | 0.984 | 0.992 |
| Negative files | 1.000 | 1.000 |
| Documents with a second OCR | 0 | 1 (appeal 0009) |

A wider rule (all documents without a type, and `numer_transakcji`) gave a second OCR to 10 documents and the same F1. The text path does not change: organizer dev / holdout 1.000, OCR train / val 0.9874 / 0.9818.

## 2026-11-22 (main): more edge cases from the real scans

The errors come from the real scans of the test split (see the entry below). All fixes are general.

- `odwolanie.LISTED_ACTION_RE`: a page footer or a stamp can stand between "wnoszę odwołanie wobec:" and the first item. Example: "Siedziba: ... WPŁYNĘŁO 1 1. czynności ...".
- `odwolanie.parse_procurement`: the OCR can lose the slash in the BZP number: "2026 BZP 00239965/01".
- `odwolanie.ANCHOR_RE`: "reprezentowany przez.pełnomocnika:" with a dot.
- `ocr.repair_emails`: a comma for a dot before "@": "a,wrobel@...".
- `pelnomocnictwo.find_attorneys`: a name with a PESEL in parentheses is an attorney: "Anna Nowak (pracownik Mocodawcy, PESEL: ...) oraz Piotr Wróbel (...)".
- `pelnomocnictwo.find_declarant`: "niżej podpisany/a Jan Nowak".
- `przelew.join_label_tails`: the second word of a label can stand on the next line, in small letters: "Numer 305494" and then "transakcji".
- New tests for each case.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1 and 2 | no change | no change |
| OCR train / val | 0.9873 / 0.9804 | 0.9874 / 0.9811 |
| OCR test, all (not independent now) | 0.9612 | 0.9666 |
| OCR real scans 0005-0010 (not independent now) | 0.935 | 0.984 |

## 2026-11-22 (main): edge cases from the real scans of the test split

The team decided to read the errors of the real scans 0005-0010 (test split). The hidden test set of the jury has documents of the same kind. From now on, the test split is not an independent measurement. Each fix must be general and must not change the results of the other test sets.

- `config/types/przelew.yaml`:
  - A printout that starts with "Przelew krajowy" (or SEPA, natychmiastowy) gets 4 points. Before, the scan 0008 had 4 points and the minimum is 5.
  - "kontrahent" is a word for the recipient.
  - "Szczegóły płatności" is a label of the title.
  - A line "Signature Not Verified" or "podpisany" stops the title.
- `ocr.repair`: "Sp. z 0.0." becomes "Sp. z o.o.". Before, only "sp." with a small letter was repaired.
- `pelnomocnictwo.find_attorneys`: a profession after a dash marks an attorney: "1. Sylwia Sikora – adwokat, nr wpisu ...".
- `pelnomocnictwo.assign_signers`: the text can name the signer after "reprezentowana przez". Then the signer belongs to the company that the text names last before this phrase.
- New tests in `tests/test_ocr.py`, `tests/test_przelew.py` and `tests/test_pelnomocnictwo.py`.

| Test set | Before | After |
|---|---|---|
| Organizer dev / holdout (text) | 1.000 / 1.000 | 1.000 / 1.000 |
| Generator 1 and 2 | no change | no change |
| OCR train / val | 0.9873 / 0.9797 | 0.9873 / 0.9804 |
| OCR real scans 0005-0010 (not independent now) | 0.895 | 0.935 |

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
