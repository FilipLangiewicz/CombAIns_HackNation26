"""Start the application from the root folder: python main.py [--input input] [--output output]."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from odw2json.cli import main  # noqa: E402

main()
