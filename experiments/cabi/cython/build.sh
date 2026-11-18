#!/bin/bash
# Build the Cython-over-C-ABI prototype (bcy.pyx) as ONE static abi3 module: the bclibc core and the C ABI wrapper
# (bclibc_ffi.cpp) are compiled into it, so it needs no shared library and no C++ API in Cython.
#
#   PYTHON=<python with Cython >= 3.1 and the Python headers>  ./build.sh      ->  build/bcy.abi3.so
#   BCLIBC=<bclibc checkout>   (default: the submodule of this repository, which must be initialised)
#   PYTHONPATH=build python -c "import bcy"
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
PY=${PYTHON:-python3}
B=${BCLIBC:-$REPO/py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc}
OUT=${OUT:-$HERE/build}
[ -f "$B/src/ffi/bclibc_ffi.cpp" ] || { echo "no bclibc sources in $B (git submodule update --init, or set BCLIBC)"; exit 1; }
rm -rf "$OUT"; mkdir -p "$OUT/obj"
INC=$($PY -c "import sysconfig; print(sysconfig.get_paths()['include'])")

# bclibc/version.h is made by CMake: write it the way py_ballisticcalc.ctypes does
$PY - "$REPO" "$B" "$OUT/gen" <<'PYEOF'
import sys
from pathlib import Path
repo, bclibc, out = sys.argv[1:4]
sys.path.insert(0, str(Path(repo) / "py_ballisticcalc.ctypes"))
import _bclibc
_bclibc.write_version_header(Path(bclibc), Path(out))
PYEOF

# the module: pyx -> C (the declarations of the C ABI are in bcffi.pxd)
(cd "$HERE" && $PY -m cython -3 -I "$HERE" bcy.pyx -o "$OUT/bcy.c")
gcc -fPIC -O2 -fvisibility=hidden -D__CYTHON__=1 -DPy_LIMITED_API=0x030B0000 -I"$INC" -I"$B/include" -c "$OUT/bcy.c" -o "$OUT/bcy_module.o"

# the core and the C ABI wrapper, as py_ballisticcalc.ctypes builds them, but with hidden visibility: only PyInit_bcy is exported
CXXF="-std=c++17 -O3 -fno-exceptions -fno-rtti -ffp-contract=off -fPIC -fvisibility=hidden -fvisibility-inlines-hidden \
 -ffunction-sections -fdata-sections -I$B/include -I$B/include/bclibc -I$B/src -I$OUT/gen"
for s in interp base_types traj_data traj_filter engine euler rk4 cash_karp dormand_prince tsitouras velocity_verlet ffi/bclibc_ffi; do
  echo "$B/src/$s.cpp"
done | xargs -P "$(nproc)" -I{} sh -c 'g++ '"$CXXF"' -c {} -o '"$OUT"'/obj/$(basename {} .cpp).o'

g++ -shared -static-libstdc++ -static-libgcc -Wl,--gc-sections -Wl,--version-script="$HERE/bcy.map" -Wl,-strip-all \
  "$OUT/bcy_module.o" "$OUT"/obj/*.o -o "$OUT/bcy.abi3.so"
ls -l "$OUT/bcy.abi3.so" | awk '{printf "built %s (%d bytes)\n", $9, $5}'
