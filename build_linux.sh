#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -x .venv/bin/flet ]]; then
    FLET=.venv/bin/flet
elif command -v flet >/dev/null 2>&1; then
    FLET=flet
else
    echo "Flet is not installed. Set up the project environment with:" >&2
    echo "  python3 -m venv .venv" >&2
    echo "  .venv/bin/python -m pip install -r requirements.txt" >&2
    exit 1
fi

"$FLET" pack main.py --name CVault --add-data assets:assets --distpath dist/linux -y
