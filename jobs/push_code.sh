#!/usr/bin/env bash
# Upload the code of the last commit as the private Kaggle dataset <user>/odw2json-code.
# The repository is private, so a kernel cannot clone it. The kernel reads this dataset.
# Usage: bash jobs/push_code.sh [@<suffix>]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="$(bash "$ROOT/jobs/kaggle.sh" "$@" config view | sed -n 's/.*username: //p')"
DIR="$(mktemp -d)"
COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
git -C "$ROOT" archive --format=zip -o "$DIR/odw2json-code.zip" HEAD src config main.py requirements.txt
echo "$COMMIT" > "$DIR/commit.txt"
printf '{"title": "odw2json-code", "id": "%s/odw2json-code", "licenses": [{"name": "other"}]}\n' "$USER_NAME" \
  > "$DIR/dataset-metadata.json"
NOTE="commit $COMMIT"
if bash "$ROOT/jobs/kaggle.sh" "$@" datasets status "$USER_NAME/odw2json-code" > /dev/null 2>&1; then
  bash "$ROOT/jobs/kaggle.sh" "$@" datasets version -p "$DIR" -m "$NOTE" -q
else
  bash "$ROOT/jobs/kaggle.sh" "$@" datasets create -p "$DIR" -q
fi
echo "uploaded $NOTE to $USER_NAME/odw2json-code"
