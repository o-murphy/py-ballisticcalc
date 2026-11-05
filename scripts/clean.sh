#!/usr/bin/env bash
# Remove build artifacts of the cythonized extensions.
# Usage: scripts/clean.sh [--all]
#   --all   also remove .venv and all __pycache__ directories
# Afterwards `uv sync --extra exts` rebuilds the extensions.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

EXTS=py_ballisticcalc.exts
PKG=$EXTS/py_ballisticcalc_exts

echo "--- Removing extension build artifacts ---"
rm -rfv py_ballisticcalc_exts.egg-info \
    "$EXTS"/*.egg-info \
    "$EXTS/build" "$EXTS/dist" \
    "$PKG/build" \
    build dist
find "$PKG" -maxdepth 1 -type f \( -name "*.pyd" -o -name "*.so" -o -name "*.html" \) -print -delete

if [[ "${1:-}" == "--all" ]]; then
    echo "--- Removing virtual environment and caches ---"
    rm -rf .venv
    find . -type d -name "__pycache__" -not -path "./.git/*" -prune -exec rm -rf {} +
fi
echo "--- Cleanup complete. ---"
