"""Make the OCR boxes of four shards of the synthetic scan data set (odw2json.scans) on the CPU."""

import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

SHARDS = [0, 1, 2, 3]
N_SHARDS = 60
CODENAME = "ocr-set-v5a"
DATA_REPO = "https://github.com/Urzad-Zamowien-Publicznych/hacknation-2026.git"
CODE = Path("/tmp/code")  # Not in the output folder, so the code is not an output.
OUT = Path("/kaggle/working") / CODENAME

pip = [sys.executable, "-m", "pip", "install", "-q"]
subprocess.run([*pip, "rapidocr", "onnxruntime", "pypdfium2", "pdfplumber"], check=True)
archive = next(Path("/kaggle/input").rglob("odw2json-code.zip"), None)
if archive:
    zipfile.ZipFile(archive).extractall(CODE)
else:
    # Kaggle can extract an uploaded zip into a folder.
    shutil.copytree(next(Path("/kaggle/input").rglob("main.py")).parent, CODE)
commit = next(Path("/kaggle/input").rglob("commit.txt")).read_text().strip()
print("commit", commit, flush=True)
subprocess.run(["git", "clone", "-q", "--depth", "1", DATA_REPO, str(CODE / "data" / "uzp")], check=True)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "commit.txt").write_text(commit)

procs = {}
for shard in SHARDS:
    # One process for each core, with one thread in each process.
    env = os.environ | {
        "PYTHONPATH": str(CODE / "src"),
        "ODW2JSON_OCR_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "ODW2JSON_OCR_CACHE": f"/kaggle/temp/cache{shard}",
    }
    out = OUT / f"ocr-shard-{shard}.jsonl"
    cmd = [sys.executable, "-m", "odw2json.scans", "--shard", str(shard), "--shards", str(N_SHARDS), "--out", str(out)]
    log = open(OUT / f"shard-{shard}.txt", "w")  # noqa: SIM115
    procs[shard] = subprocess.Popen(cmd, cwd=CODE, env=env, stdout=log, stderr=subprocess.STDOUT)


def count(shard: int) -> int:
    path = OUT / f"ocr-shard-{shard}.jsonl"
    return sum(1 for _ in path.open()) if path.exists() else 0


start = time.time()
while any(p.poll() is None for p in procs.values()):
    time.sleep(60)
    print(f"{(time.time() - start) / 60:.0f} min, documents: {[count(s) for s in SHARDS]}", flush=True)
print("exit codes", [p.returncode for p in procs.values()], flush=True)
for shard in SHARDS:
    print((OUT / f"shard-{shard}.txt").read_text()[-800:], flush=True)
