#!/usr/bin/env bash
# Build the exts package with AddressSanitizer + UBSan (and Cython bounds/overflow checks) and run its tests and the core tests.
# Usage: scripts/test-asan.sh [extra pytest args...]     (Linux, gcc)
# Afterwards reinstall the normal build: uv sync --reinstall --extra exts --extra ctypes
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

san="-fsanitize=address,undefined -fno-omit-frame-pointer -O1 -g"
rm -rf py_ballisticcalc.exts/build
CFLAGS="$san" CXXFLAGS="$san" LDFLAGS="-fsanitize=address,undefined" \
    CYTHON_SAFETY=1 CYTHON_FORCE_REGEN=1 DISABLE_SHARED_STRIP=1 \
    uv pip install --reinstall --no-deps ./py_ballisticcalc.exts

# the interpreter is not instrumented: preload the runtimes (valgrind-free, detect_leaks=0 as CPython "leaks" at exit)
export LD_PRELOAD="$(gcc -print-file-name=libasan.so):$(gcc -print-file-name=libubsan.so)"
export ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=1 UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 PYTHONMALLOC=malloc

.venv/bin/python -m pytest py_ballisticcalc.exts/tests -q -m "stress or not stress" "$@"
for engine in cython+dopri cython+rk4; do
    .venv/bin/python -m pytest tests -q --engine="$engine" "$@"
done
