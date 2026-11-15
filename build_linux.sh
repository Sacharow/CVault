#!/usr/bin/env bash
set -euo pipefail

if ! command -v flet >/dev/null 2>&1; then
    echo "Flet is not installed. Run: python3 -m pip install -r requirements.txt" >&2
    exit 1
fi

flet pack main.py --name CVault --add-data assets:assets
