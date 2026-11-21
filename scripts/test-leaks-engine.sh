#!/usr/bin/env bash
# Leak check of one native engine (ctypes+<method> or cython+<method>) under Valgrind, Linux only.
# Usage: scripts/test-leaks-engine.sh <engine> [iterations]        (default 200)
#
# The same workload runs once and then `iterations` times; the bytes "definitely lost" must not grow with the iterations (the
# interpreter's own one-time allocations are the same in both). Valgrind reports of the Python interpreter are not suppressed, so
# the report is compared, not read. Logs: valgrind-<engine>-1.log and valgrind-<engine>-<iterations>.log in the current directory.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

engine="${1:?usage: $0 <engine> [iterations]}"
iterations="${2:-200}"
command -v valgrind >/dev/null || { echo "valgrind is required" >&2; exit 1; }

# the native variant to test must be installed in .venv (see the README of its package)
export PYTHONMALLOC=malloc PYTHONWARNINGS=ignore

definitely_lost() {
    # "definitely lost: 2,168,613 bytes in 38,091 blocks" -> the byte count
    grep -E 'definitely lost:' "$1" | head -1 | sed -E 's/.*definitely lost: ([0-9,]+) bytes.*/\1/' | tr -d ,
}

for n in 1 "$iterations"; do
    log="valgrind-${engine//[+.]/_}-$n.log"
    valgrind --tool=memcheck --leak-check=full --show-leak-kinds=definite --num-callers=30 --log-file="$log" \
        -- .venv/bin/python scripts/leak_loop.py "$engine" "$n" > /dev/null
done

first="$(definitely_lost "valgrind-${engine//[+.]/_}-1.log")"
last="$(definitely_lost "valgrind-${engine//[+.]/_}-$iterations.log")"
delta=$((last - first))
echo "$engine: definitely lost 1 iteration: ${first} bytes, $iterations iterations: ${last} bytes (delta ${delta})"
if [ "$delta" -gt 4096 ]; then
    echo "possible leak: the lost bytes grow with the iterations (more than 4 KiB)" >&2
    exit 1
fi
