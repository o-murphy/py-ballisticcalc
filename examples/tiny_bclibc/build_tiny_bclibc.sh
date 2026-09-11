#!/usr/bin/env bash
# Build tiny_bclibc as a shared library for the example engines in this directory
# (py_ballisticcalc.engines.tiny_bclibc_sp is NOT a thing -- see sp.py / dp.py here).
#
# Usage:
#   ./build_tiny_bclibc.sh [bclibc-checkout-dir] [single|double]
#
# bclibc-checkout-dir defaults to ./bclibc (cloned from ballistics-lab/bclibc if missing).
# precision defaults to "single".
#
# single precision -> <bclibc-checkout-dir>/tiny_bclibc/build/libtiny_bclibc.so
#                      (point sp.py's PYBALLISTICCALC_TINY_BCLIBC_LIB at this)
# double precision -> <bclibc-checkout-dir>/tiny_bclibc/build_double/libtiny_bclibc.so
#                      (point dp.py's PYBALLISTICCALC_TINY_BCLIBC_DP_LIB at this)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BCLIBC_DIR="${1:-${SCRIPT_DIR}/bclibc}"
PRECISION="${2:-single}"

if [ "${PRECISION}" != "single" ] && [ "${PRECISION}" != "double" ]; then
    echo "error: precision must be 'single' or 'double', got '${PRECISION}'" >&2
    exit 1
fi

if [ ! -d "${BCLIBC_DIR}" ]; then
    echo "Cloning ballistics-lab/bclibc into ${BCLIBC_DIR} ..."
    git clone --depth 1 https://github.com/ballistics-lab/bclibc.git "${BCLIBC_DIR}"
fi

TINY_DIR="${BCLIBC_DIR}/tiny_bclibc"
if [ ! -d "${TINY_DIR}" ]; then
    echo "error: ${TINY_DIR} not found (unexpected bclibc layout)" >&2
    exit 1
fi

if [ "${PRECISION}" = "single" ]; then
    BUILD_DIR="${TINY_DIR}/build"
    SINGLE_PRECISION_FLAG="ON"
    ENV_VAR="PYBALLISTICCALC_TINY_BCLIBC_LIB"
else
    BUILD_DIR="${TINY_DIR}/build_double"
    SINGLE_PRECISION_FLAG="OFF"
    ENV_VAR="PYBALLISTICCALC_TINY_BCLIBC_DP_LIB"
fi

echo "Configuring tiny_bclibc (${PRECISION} precision, shared) in ${BUILD_DIR} ..."
cmake -B "${BUILD_DIR}" -S "${TINY_DIR}" \
    -DTINY_BCLIBC_BUILD_SHARED=ON \
    -DTINY_BCLIBC_SINGLE_PRECISION="${SINGLE_PRECISION_FLAG}" \
    -DCMAKE_BUILD_TYPE=Release

echo "Building ..."
cmake --build "${BUILD_DIR}" --config Release

case "$(uname -s)" in
    Darwin) LIB_NAME="libtiny_bclibc.dylib" ;;
    MINGW*|MSYS*|CYGWIN*) LIB_NAME="tiny_bclibc.dll" ;;
    *) LIB_NAME="libtiny_bclibc.so" ;;
esac

LIB_PATH="${BUILD_DIR}/${LIB_NAME}"
if [ ! -f "${LIB_PATH}" ]; then
    # Windows multi-config generators put the DLL under a config subdirectory.
    LIB_PATH="$(find "${BUILD_DIR}" -name "${LIB_NAME}" -print -quit)"
fi

if [ -z "${LIB_PATH}" ] || [ ! -f "${LIB_PATH}" ]; then
    echo "error: build finished but ${LIB_NAME} was not found under ${BUILD_DIR}" >&2
    exit 1
fi

echo
echo "Built (${PRECISION} precision): ${LIB_PATH}"
echo
echo "Point py_ballisticcalc at it with:"
echo "  export ${ENV_VAR}=${LIB_PATH}"
