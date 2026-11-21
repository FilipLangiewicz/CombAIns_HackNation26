#!/usr/bin/env bash
# Run the Kaggle CLI of the project with the correct account.
# Usage: bash jobs/kaggle.sh [@<suffix>] <arguments of the kaggle command>
# Without @<suffix>, the CLI uses .kaggle/access_token. With @c, it uses .kaggle/access_token_c.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOKEN="$ROOT/.kaggle/access_token"
if [[ "${1:-}" == @* ]]; then
  TOKEN="$ROOT/.kaggle/access_token_${1#@}"
  shift
fi
# The value, not the path: a Windows Python does not know the Git Bash paths.
if [ -s "$TOKEN" ]; then
  export KAGGLE_API_TOKEN="$(tr -d '[:space:]' < "$TOKEN")"
fi
for KAGGLE in "$ROOT/.venv/Scripts/kaggle.exe" "$ROOT/.venv/bin/kaggle"; do
  [ -x "$KAGGLE" ] && exec "$KAGGLE" "$@"
done
echo "kaggle.sh: no Kaggle CLI in $ROOT/.venv" >&2
exit 127
