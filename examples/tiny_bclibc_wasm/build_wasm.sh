#!/usr/bin/env bash
# Builds the two WebAssembly modules the engines in this directory load (__init__.py):
#
#   build/tiny_bclibc_dp.wasm   real_t = double
#   build/tiny_bclibc_sp.wasm   real_t = float
#
# Usage (from the repo root):
#   git submodule update --init py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc
#   examples/tiny_bclibc_wasm/build_wasm.sh
#
# The build itself (wrapper C source + toolchain selection) lives in bclibc as
# tiny_bclibc/build_wasm.sh; this only runs it against the same bclibc submodule the Cython
# engine and examples/tiny_bclibc use (one pinned bclibc per repo -- see
# examples/tiny_bclibc/CMakeLists.txt). Toolchain: see that script (`pip install ziglang` is
# enough). TINY_BCLIBC_DIR=/path/to/bclibc/tiny_bclibc builds against another checkout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SUBMODULE_DIR="${REPO_ROOT}/py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc"
TINY_BCLIBC_DIR="${TINY_BCLIBC_DIR:-${SUBMODULE_DIR}/tiny_bclibc}"

if [[ ! -f "${TINY_BCLIBC_DIR}/include/tiny_bclibc/engine.h" ]]; then
    echo "tiny_bclibc not found at ${TINY_BCLIBC_DIR}." >&2
    echo "Run from the repo root: git submodule update --init py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc" >&2
    exit 1
fi
if [[ ! -x "${TINY_BCLIBC_DIR}/build_wasm.sh" ]]; then
    echo "${TINY_BCLIBC_DIR} predates tiny_bclibc/build_wasm.sh (the WebAssembly build this engine loads)." >&2
    echo "Update the bclibc submodule to a commit that has it." >&2
    exit 1
fi

OUT_DIR="${SCRIPT_DIR}/build" "${TINY_BCLIBC_DIR}/build_wasm.sh"
