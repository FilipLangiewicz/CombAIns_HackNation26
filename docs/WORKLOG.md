# Worklog

Add new entries at the top. Each entry has the date, the branch and the changes.

## 2026-11-21 (rule-pipeline)

- Add the pipeline: text from the PDF, the classifier from `config/types/*.yaml`, one extractor for each type.
- Add the F1 evaluation with the rules of the organizer, and a fixed split in `config/split.json` (45 dev cases, 15 holdout cases).
- Add the robustness test `odw2json.perturb`.
- Add the web interface (`python main.py --gui`), `start.bat`, `start.sh`, and the `input/` and `output/` folders.

| Run | Commit | LLM | F1 dev | F1 holdout | Time for one document |
|---|---|---|---|---|---|
| Rules only, no OCR | 3c28e57 | none | 1.0000 | 1.0000 | 0.01 s |

The scans are not in this result, because OCR is not available yet. The classification of the 16 negative documents is correct.

## 2026-11-21 (main)

- Rename `AGENTS.md` to `CLAUDE.md`. Claude Code reads this file automatically.

- Add the answers of the organizer from Discord and notes about the data to `docs/project.md`.
- Prepare the repository: `AGENTS.md`, `KAGGLE.md`, `.gitignore`, `README.md`, `docs/project.md` and the files of the environment.
- Add the materials of the challenge to `docs/task/`, with copies of the organizer README and of the JSON structures in `docs/task/organizer/`.
