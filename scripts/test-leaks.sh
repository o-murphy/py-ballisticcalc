#!/usr/bin/env bash
# Run the stress suite of the cythonized extensions under Valgrind (Linux only).
# Usage: scripts/test-leaks.sh [extra pytest args...]
# Output is saved to valgrind.log in the current directory.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

command -v valgrind >/dev/null || { echo "valgrind is required" >&2; exit 1; }

# Rebuilds the extensions only if their sources/build flags changed (see [tool.uv] cache-keys)
uv sync --extra exts

ulimit -n 65536
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all --track-origins=yes \
    -- uv run pytest -m stress ./py_ballisticcalc.exts/tests "$@" 2> valgrind.log
