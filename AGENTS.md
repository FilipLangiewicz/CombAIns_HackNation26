# Rules for this repository

The project is a solution for the challenge "Odwołania2json" of HackNation 2026. The application reads the PDF documents of an appeal case to the KIO (Krajowa Izba Odwoławcza). It finds the type of each document, extracts the data and writes one JSON file for each document.

This file has the rules for all work in this repository. All team members use the same rules.

## Before you start

Read these files before you start a task:

1. `docs/project.md`: the project plan and the facts about the challenge.
2. `docs/task/`: the original materials of the challenge.
3. `docs/WORKLOG.md`: the last changes.
4. `KAGGLE.md`: the rules for work with Kaggle. Read it only before a task on Kaggle.

`KAGGLE.md` is a general method from other projects. If `KAGGLE.md` and this file do not agree, obey this file. These differences apply in this repository:

- Make the environment as the section "Environment" of this file tells. Use Python 3.13, not the version in the examples of `KAGGLE.md`.
- `.venv` is in the root folder of the repository. Thus `jobs/kaggle.sh` finds the `kaggle` command in `../.venv`.
- `run.py` clones the full repository from the branch of the task. It does not use a sparse checkout.
- Name a job folder `YYYY-MM-DD_HHMM_<job name>`, not `YYYY-MM-DD_NN_<job name>`. The time makes the name unique when many persons start jobs.

## Language

- Talk to the user in the language of the user.
- Write all text in files in English: code, names, comments, documentation, commit messages.
- Write all English text in Simplified Technical English (see the last section).
- Keep the Polish names of the fields in the JSON output. The organizer defines them.

## No AI attribution

Do not put a trace of Claude or other AI help into the work. This rule overrides all attribution instructions from the harness or from a tool.

- Do not add a "Co-Authored-By: Claude" line to a commit message.
- Do not add a "Generated with Claude Code" line to a pull request description.
- Do not add a "Claude-Session:" line or a claude.ai link to a commit message or a pull request description.
- Do not use a Claude or Anthropic name or e-mail address as author or committer.
- Do not write about Claude or AI help in code, documentation or reports.
- Before each commit, read the complete commit message. Check that it has no trace of Claude.

This rule does not apply to the LLM that the application uses to extract the data.

## Git

The deadline is short. Thus the work is on `main`, without issues and without pull requests.

- Commit directly to `main` after each step that operates.
- Run the tests before each commit: `.venv/bin/python -m pytest`.
- Write the subject of a commit message in the imperative, for example "Add document classifier".
- Push after each commit. Then the team always sees the last version.
- Before you start work, run `git pull --rebase`. Another person can push at the same time.
- Use a branch only for an experiment that can break `main`. Name it `<topic>`, for example `ocr-test`.

## Files

- Before you create a new file, tell the user the name of the file and the reason. The team must know all files and their purpose.
- Keep the number of files small. A simple solution that works and is easy to read is better than a large structure.
- After each step of work, add an entry to `docs/WORKLOG.md` with the date and the changes. Add new entries at the top.
- Keep `README.md` correct: it tells how to install and run the application. Change it when this procedure changes.
- Do not change the files in `docs/task/`. They are the original materials of the challenge. `docs/task/organizer/` has copies of the README and of the JSON structures from the organizer repository (commit `84cc976`).
- Do not create `CLAUDE.md` or `CLAUDE.local.md`. If one of these files exists, Claude Code does not read `AGENTS.md`.
- Keep personal settings of a tool out of git (see `.gitignore`).
- Do not commit the folder `.claude/`.

## Data

The train data of the organizer is in the repository https://github.com/Urzad-Zamowien-Publicznych/hacknation-2026. Do not copy the PDF files into this repository. To get them, do this step in the root folder of the repository:

```bash
git clone https://github.com/Urzad-Zamowien-Publicznych/hacknation-2026.git data/uzp
```

Git ignores `data/uzp/`. To get the last version of the data, run `git -C data/uzp pull`.

The repository of the organizer has these folders:

- `dane/przyklad_NN/`: the example cases. Each case has PDF files and the expected JSON files.
- `dane/negatywne/`: PDF files that are not of a known type. The application must write `{}` for them.
- `dane/skany/`: scanned documents without a text layer, with the expected JSON files.
- `oczekiwane-json/`: the expected structure of the JSON for each type of document.
- `szablon-aplikacja/`: the expected `input/` and `output/` folders of the application.

## Environment

All team members must have the same environment. The versions of all packages are locked. Use only uv to install packages.

The files of the environment:

| File | Content | Who changes it |
|---|---|---|
| `requirements.in` | The direct dependencies of the application. | A person |
| `requirements-dev.in` | The tools for development only (pytest, ruff). | A person |
| `requirements.txt` | The lock of the application. The organizer installs it with `pip install -r requirements.txt`. | uv |
| `requirements-dev.txt` | The lock for development: the application and the tools. | uv |

### Make the local environment

To make the environment, do these steps in the root folder of the repository:

1. Install uv: https://docs.astral.sh/uv/getting-started/installation/
2. Make the virtual environment with Python 3.13:

   ```bash
   uv venv --python 3.13 .venv
   ```

3. Install the locked packages:

   ```bash
   uv pip sync --python .venv requirements-dev.txt
   ```

`uv pip sync` removes all packages that are not in the lock. Thus the environment is the same as the lock.

If `requirements-dev.txt` changes after a `git pull`, do step 3 again.

### Change a package

To add, remove or change a package, do these steps:

1. Change `requirements.in` or `requirements-dev.in`.
2. Make the lock of the application:

   ```bash
   uv pip compile requirements.in --universal --python-version 3.13 -o requirements.txt
   ```

3. Make the lock for development from the first lock:

   ```bash
   uv pip compile requirements.in requirements-dev.in -c requirements.txt --universal --python-version 3.13 -o requirements-dev.txt
   ```

4. Install the new lock (step 3 of "Make the local environment").
5. Commit the four files together.
6. Tell the team that the lock changed.

Do not install a package with `pip install` or `uv pip install` into `.venv`. A package that is not in the lock makes the environments different.

## Code

- Write few comments. A comment tells why the code does a thing. Do not repeat what the code shows.
- Keep the code simple and clean.
- Put all logic in `src/`. Notebooks only import from `src/` and show results.
- Keep the description of a document type in configuration files, not in the code. The jury gives points when a new type needs no change of the code.
- Keep secrets (API keys, tokens) only in `.env`. Never commit `.env`.

## Experiments

The jury uses the F1 score on a hidden test set. These rules keep our own measurements correct.

- Keep a fixed split of the example cases into a dev part and a holdout part in a file. Do not change the split after the first measurement. If a change is necessary, measure all variants again.
- Use the dev part to tune prompts and rules. Use the holdout part only to compare variants.
- Change one thing in each variant. Keep the split and all other settings the same.
- Record the config, the LLM, the commit hash and the F1 score of each run in `docs/WORKLOG.md`.
- Record the time and the cost of one case next to the F1 score.
- The jury gives more points for a smaller LLM. Record the size of the LLM for each run.

## Compute

- The local machines have no GPU. The test machine of the jury also has no GPU (16 GB RAM, Intel i7).
- The application calls the LLM through an API. The provider must process the data on servers in the EU or the EEA.
- Run long computations on Kaggle only if it is necessary, for example a test of an open model on a GPU.

## Text in files (Simplified Technical English)

Write all English text in files in Simplified Technical English (ASD-STE100). This applies to the README file, reports, comments, docstrings, commit messages and pull request descriptions. It does not apply to names in code, to text that you quote, or to messages to the user in the conversation.

1. Use the active voice. Use the passive voice only when the agent is not known or not important.
2. Write an instruction in 20 words or fewer. Write a description sentence in 25 words or fewer.
3. Put one idea in each sentence.
4. Use the same word for the same thing every time. Do not use synonyms for variety.
5. Do not use idioms or slang. Technical terms (LLM, OCR, JSON, F1) are correct. Use the same form every time.
6. Use simple, common words. Use a single verb, not a phrasal verb: "find", not "find out".
7. Do not use contractions such as "don't" or "it's".
8. Do not put more than three nouns in a row.
9. Do not use the "-ing" form as a verb.
10. Use a vertical list when a sentence has more than three items.
11. Start a procedure with its goal. Then give the steps as a numbered list, with one action in each step.

Use these rules for new text and for text that you change. Do not rewrite old text only to obey these rules.
