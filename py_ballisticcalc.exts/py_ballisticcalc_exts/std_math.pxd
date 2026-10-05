# C++ <cmath>/<limits> declarations without `except +`.
#
# libcpp.cmath declares these with `except +` (and libc.math has its own C-level spellings), which makes Cython
# wrap every call in try/catch -- not compilable with -fno-exceptions. These are plain `noexcept` externs on the
# std:: functions, usable from nogil code, so no Python-level `import math` is needed either.
cdef extern from "<cmath>" namespace "std" nogil:
    bint isfinite(double x) noexcept
    double sin(double x) noexcept
    double cos(double x) noexcept

cdef extern from "<limits>" namespace "std::numeric_limits<double>" nogil:
    double quiet_NaN() noexcept
