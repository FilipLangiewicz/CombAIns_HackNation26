"""Make the OCR text of shards of the synthetic scan data set (odw2json.scans), one shard on each GPU."""

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SHARDS = [4,5]
N_SHARDS = 6
CODENAME = "ocr-set-v1c"
DATA_REPO = "https://github.com/Urzad-Zamowien-Publicznych/hacknation-2026.git"
CODE = Path("/tmp/code")  # Not in the output folder, so the code is not an output.
OUT = Path("/kaggle/working") / CODENAME

if len(sys.argv) == 1:
    pip = [sys.executable, "-m", "pip", "install", "-q"]
    subprocess.run([*pip, "rapidocr", "pypdfium2", "pdfplumber"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "-q", "onnxruntime"], check=False)
    subprocess.run([*pip, "onnxruntime-gpu"], check=True)
    archive = next(Path("/kaggle/input").rglob("odw2json-code.zip"), None)
    if archive:
        zipfile.ZipFile(archive).extractall(CODE)
    else:  # Kaggle extracts an uploaded zip into a folder.
        shutil.copytree(next(Path("/kaggle/input").rglob("main.py")).parent, CODE)
    commit = next(Path("/kaggle/input").rglob("commit.txt")).read_text().strip()
    print("commit", commit, flush=True)
    subprocess.run(["git", "clone", "--depth", "1", DATA_REPO, str(CODE / "data" / "uzp")], check=True)
    import onnxruntime

    print("providers", onnxruntime.get_available_providers(), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "commit.txt").write_text(commit)
    procs = []
    for gpu, shard in enumerate(SHARDS):
        env = os.environ | {"CUDA_VISIBLE_DEVICES": str(gpu), "PYTHONPATH": str(CODE / "src"),
                            "ODW2JSON_OCR_CUDA": "1", "ODW2JSON_OCR_CACHE": f"/kaggle/temp/cache{gpu}"}  # fmt: skip
        cmd = [sys.executable, "-m", "odw2json.scans", "--shard", str(shard), "--shards", str(N_SHARDS),
               "--out", str(OUT / f"ocr-shard-{shard}.jsonl")]  # fmt: skip
        log = open(OUT / f"shard-{shard}.txt", "w")  # noqa: SIM115
        procs.append(subprocess.Popen(cmd, cwd=CODE, env=env, stdout=log, stderr=subprocess.STDOUT))
    codes = [p.wait() for p in procs]
    print("exit codes", codes, flush=True)
    for shard in SHARDS:
        print(open(OUT / f"shard-{shard}.txt").read()[-1500:], flush=True)
