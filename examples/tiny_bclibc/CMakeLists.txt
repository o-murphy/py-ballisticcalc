# Builds tiny_bclibc as shared libraries (single- and double-precision) for the example
# engines in this directory (sp.py / dp.py).
#
# Usage (from repo root, after `git submodule update --init`):
#   cmake -B examples/tiny_bclibc/build -S examples/tiny_bclibc
#   cmake --build examples/tiny_bclibc/build
#
# Then point the engines at the results:
#   export PYBALLISTICCALC_TINY_BCLIBC_LIB=$(pwd)/examples/tiny_bclibc/build/single/libtiny_bclibc.so
#   export PYBALLISTICCALC_TINY_BCLIBC_DP_LIB=$(pwd)/examples/tiny_bclibc/build/double/libtiny_bclibc.so
#
# Where bclibc comes from:
#   py-ballisticcalc already carries bclibc as a single git submodule at
#   py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc (used to build the Cython
#   engine). This example intentionally reuses that SAME checkout rather than fetching a
#   second copy of bclibc -- two independently-pinned copies in one repo would let the
#   Cython engine and this example silently drift onto different bclibc versions. If the
#   submodule isn't initialized, or is pinned to a commit predating
#   tiny_bclibc_integrate_raw() (the raw-streaming API these example engines call),
#   configuration fails with instructions rather than fetching around the problem.
cmake_minimum_required(VERSION 3.14)
project(tiny_bclibc_examples LANGUAGES C)

set(_submodule_dir
    "${CMAKE_CURRENT_SOURCE_DIR}/../../py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc")
set(TINY_BCLIBC_SOURCE_DIR "${_submodule_dir}/tiny_bclibc")
set(_engine_h "${TINY_BCLIBC_SOURCE_DIR}/include/tiny_bclibc/engine.h")

if(NOT EXISTS "${_engine_h}")
    message(FATAL_ERROR
        "bclibc submodule not initialized: ${_engine_h} not found.\n"
        "Run from the repo root: git submodule update --init "
        "py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc")
endif()

file(STRINGS "${_engine_h}" _raw_api_line REGEX "tiny_bclibc_integrate_raw")
if(NOT _raw_api_line)
    message(FATAL_ERROR
        "The bclibc submodule checkout at ${_submodule_dir} is pinned to a commit that "
        "predates tiny_bclibc_integrate_raw() (the raw-streaming API sp.py/dp.py call). "
        "Update the submodule to a commit that has it, e.g. from the repo root:\n"
        "  cd py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc\n"
        "  git fetch origin claude/tiny-bclibc-single-precision-9mvkk6\n"
        "  git checkout FETCH_HEAD\n"
        "  cd -\n"
        "  git add py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc")
endif()

include(ExternalProject)

foreach(_precision single double)
    if(_precision STREQUAL "single")
        set(_single_precision_flag ON)
    else()
        set(_single_precision_flag OFF)
    endif()
    ExternalProject_Add(tiny_bclibc_${_precision}
        SOURCE_DIR       ${TINY_BCLIBC_SOURCE_DIR}
        BINARY_DIR       ${CMAKE_CURRENT_BINARY_DIR}/${_precision}
        CMAKE_ARGS       -DTINY_BCLIBC_BUILD_SHARED=ON
                         -DTINY_BCLIBC_SINGLE_PRECISION=${_single_precision_flag}
                         -DCMAKE_BUILD_TYPE=Release
        BUILD_ALWAYS     TRUE
        INSTALL_COMMAND  ""
        # SOURCE_DIR already points at the submodule checkout -- skip ExternalProject's own
        # download/update machinery (it would otherwise treat SOURCE_DIR as something it owns
        # and try to manage/clean it).
        DOWNLOAD_COMMAND ""
        UPDATE_COMMAND   "")
endforeach()

add_custom_target(tiny_bclibc_print_paths ALL
    COMMAND ${CMAKE_COMMAND} -E echo
        "single precision library under: ${CMAKE_CURRENT_BINARY_DIR}/single"
    COMMAND ${CMAKE_COMMAND} -E echo
        "double precision library under: ${CMAKE_CURRENT_BINARY_DIR}/double"
    DEPENDS tiny_bclibc_single tiny_bclibc_double)
