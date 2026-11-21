# Worklog

Add new entries at the top. Each entry has the date, the branch and the changes.

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
