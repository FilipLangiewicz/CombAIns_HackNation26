#!/usr/bin/env bash
# Read the PDF files in input/ and write the JSON files to output/. Add --gui to start the web interface.
cd "$(dirname "$0")"
exec python3 main.py "$@"
