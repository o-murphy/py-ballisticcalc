# py_ballisticcalc.ctypes

The bclibc engines of [py_ballisticcalc](https://github.com/o-murphy/py-ballisticcalc) through `ctypes`: for the
interpreters the Cython extensions (`py_ballisticcalc.exts`) cannot serve, PyPy and GraalPy, and for the platforms
they are not built for, and as an alternative to them on Android. `pip install py_ballisticcalc[ctypes]` installs it; `py_ballisticcalc[exts]` is the Cython variant, and `py_ballisticcalc[native]` picks one of the two for the interpreter and the machine (ctypes on PyPy, GraalPy, ppc64le, s390x and riscv64).

The wheel is `py3-none-<platform>`: the `bclibc_ffi` library has a C ABI and does not depend on the interpreter.

Status: the library build (`setup.py`), the ctypes bindings (`regenerate_bindings.py`) and the wheels are in place; the
engines on top of them are not ported yet.
