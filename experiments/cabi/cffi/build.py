import sys
from pathlib import Path
from cffi import FFI
W = Path(__file__).parent
B = Path(sys.argv[1])
LIB = Path(sys.argv[2])
ffi = FFI()
ffi.cdef((W / "header_pp.h").read_text())
ffi.set_source(
    "_bcffi",
    '#include "bclibc/ffi/bclibc_ffi.h"',
    include_dirs=[str(B / "include")],
    library_dirs=[str(LIB)],
    libraries=["bclibc_ffi"],
    extra_link_args=[f"-Wl,-rpath,{LIB}"],
    py_limited_api=True,
)
if __name__ == "__main__":
    ffi.compile(tmpdir=str(W), verbose=True)
    print("emitted _bcffi.c")
