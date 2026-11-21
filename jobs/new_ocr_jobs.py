"""Make the job folders for the OCR of the scan data set, spread over all Kaggle accounts.

Each account runs at most 5 CPU sessions at the same time. Each session has 4 cores, so it runs 4 shards.
Usage: python jobs/new_ocr_jobs.py <job name prefix> [--kernels-per-account 5]
Then push each folder with the account in the "account" file of the folder (see jobs/JOBS.md).
"""

import argparse
import json
import string
from datetime import datetime
from pathlib import Path

ACCOUNTS = {"": "combainsidm", "@n": "nataliachoszczyk", "@f": "gpla77"}
JOBS = Path(__file__).resolve().parent
TEMPLATE = JOBS / "ocr_run_template.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", help="for example ocr-set-v3")
    parser.add_argument("--kernels-per-account", type=int, default=5)
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    kernels = [(flag, user) for flag, user in ACCOUNTS.items() for _ in range(args.kernels_per_account)]
    n_shards = 4 * len(kernels)
    rows = []
    for k, (flag, user) in enumerate(kernels):
        name = f"{args.prefix}{string.ascii_lowercase[k]}"
        folder = JOBS / "runs" / f"{stamp}_{name}"
        folder.mkdir(parents=True)
        shards = list(range(4 * k, 4 * k + 4))
        run = TEMPLATE.read_text().replace("__SHARDS__", str(shards)).replace("__N_SHARDS__", str(n_shards))
        (folder / "run.py").write_text(run.replace("__CODENAME__", name))
        meta = {
            "id": f"{user}/odw2json-{name}",
            "title": f"odw2json-{name}",
            "code_file": "run.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": False,
            "enable_internet": True,
            "dataset_sources": [f"{user}/odw2json-code"],
            "competition_sources": [],
            "kernel_sources": [],
        }
        (folder / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        (folder / "account").write_text(flag + "\n")
        rows.append(f"| {folder.name} | {name} | {user} | OCR of the scan data set, shards {shards} of {n_shards} | to run |")
    with (JOBS / "JOBS.md").open("a") as f:
        f.write("\n".join(rows) + "\n")
    print("\n".join(str(JOBS / "runs" / r.split(" | ")[0][2:]) for r in rows))


if __name__ == "__main__":
    main()
