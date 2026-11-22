# Deployment on the VM of the organizer

The jury runs our solution on a VM in Azure, not on our machines. This file tells what must be on the VM and how we tested it. The rules of the organizer are in `data/uzp/VM.md` (the repository of the organizer, see `CLAUDE.md`, section "Data").

## The rules of the organizer

- The access of the team stops on **2026-11-22 at 11:00**. After this time, nobody of the team can log in. The jury evaluates the VM in the state that we leave.
- The jury puts the hidden documents into `/opt/solution/input`.
- The jury runs the command from `/opt/solution/RUN.md` in the folder `/opt/solution`, with `sudo`.
- The command must not ask questions. It must stop when all files are processed.
- The jury takes the JSON files from `/opt/solution/output`.
- The jury can clear `input/` and `output/` before the run. Do not keep files of the solution in these folders.
- Download all images, models and dependencies before the deadline. The jury does not guarantee internet access during the run.
- The command must also operate after a restart of the VM.

## The VM

| Item | Value |
|---|---|
| Address | `team23@74.248.18.119` |
| System | Ubuntu 24.04, 2 vCPU, 16 GB RAM, 64 GB disk, no GPU |
| Installed | Docker with Compose v2, git, Python 3.12 |
| SSH key | `~/.ssh/hacknation26_vm` on the laptop of Filip. The password is not in the repository. |

To log in, use this command:

```bash
ssh -i ~/.ssh/hacknation26_vm -o IdentitiesOnly=yes team23@74.248.18.119
```

## What is on the VM

- The files of the repository, directly in `/opt/solution`. The VM has Python 3.12, but the lock is for Python 3.13. Thus the application runs in Docker.
- The Docker image `solution-cli`. The image contains the RapidOCR models, so the run needs no internet.
- `RUN.md` with the command `docker compose run --rm cli`.
- No `.git` folder and no GitHub token. The repository is private, and the jury has access to the VM after 11:00.
- No `.env` file. The application uses no external service and no API key.

## Update the code on the VM

To send a new version of `main` to the VM, do these steps on the laptop, in the root folder of the repository:

1. Commit and push the change.
2. Send the files of the last commit:

   ```bash
   git archive --format=tar.gz HEAD | ssh -i ~/.ssh/hacknation26_vm -o IdentitiesOnly=yes team23@74.248.18.119 'cd /opt/solution && tar xzf -'
   ```

3. Build the image again on the VM:

   ```bash
   ssh -i ~/.ssh/hacknation26_vm -o IdentitiesOnly=yes team23@74.248.18.119 'cd /opt/solution && docker compose build cli'
   ```

4. Do the tests in the section "Tests" again.

`tar` does not delete files that the new commit removed. If a commit removes a file, delete it on the VM.

## Clear the output folder

The container runs as root, so the JSON files and the subfolders in `output/` belong to root. The user `team23` cannot delete a subfolder that belongs to root. To clear the folder without `sudo`, run this command on the VM:

```bash
cd /opt/solution && docker compose run --rm --entrypoint sh cli -c 'rm -rf /app/output/*'
```

Before the deadline, leave `input/` and `output/` empty.

## Tests

The deployed commit is `1ae7827`.

| Test | Result |
|---|---|
| The command from `RUN.md` on 7 files: example case 01, three real scans, one negative document | Correct. The output is the same as on the laptop. |
| All 226 PDF files of the organizer, in subfolders such as `case1/` of the template | 233 files in 434 s, exit code 0 |
| A file that is empty, truncated, random bytes, or text with the `.pdf` extension | `{}` for each file. The run continues. |
| A `.txt` file | Ignored |
| A file name with a space and the extension `.PDF` | Correct result |
| The 233 output files of the VM against the output of the same image on the laptop, without network | All files are identical |
| `sudo reboot`, then `sudo docker compose run --rm cli` on the 7 files | Docker started automatically. The output is the same as before the restart. |

A PDF file with a text layer takes less than one second. A scan takes 10 to 15 s on the VM, because the OCR runs on 2 CPU cores.
