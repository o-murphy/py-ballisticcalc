# py_ballisticcalc.ctypes

The bclibc engines of [py_ballisticcalc](https://github.com/o-murphy/py-ballisticcalc) through `ctypes`: for the interpreters the
Cython extensions (`py_ballisticcalc.exts`) cannot serve (PyPy, GraalPy), for the architectures they are not built for (ppc64le,
s390x, riscv64), and as a second variant next to them on CPython (Linux, macOS, Windows incl. x86 and ARM64, Android, Pyodide). iOS is
not built.

```bash
pip install py_ballisticcalc[ctypes]   # this package
pip install py_ballisticcalc[exts]     # the Cython variant
pip install py_ballisticcalc[native]   # one of the two for the interpreter and the machine (ctypes on PyPy, GraalPy, ppc64le, s390x, riscv64)
```

Install one of the two, not both: they register the same engine names.

## Engines

`cython+euler`, `cython+rk4`, `cython+verlet`, `cython+rkck`, `cython+dopri` and `cython+tsitouras` (entry points of the
`py_ballisticcalc.engine` group; the classes are `py_ballisticcalc_ctypes.Native<Method>IntegrationEngine`). The names are those of the
Cython engines, so `Calculator(engine="cython+dopri")` works with either package. On the benchmark of this repository (Linux x86-64,
CPython 3.13, Dormand-Prince) a full trajectory takes about 5-20% longer than with the Cython engine; it was not measured on the other
platforms.

## The wheel

`py3-none-<platform>`: one wheel per platform serves every CPython, PyPy and GraalPy it has. It carries one shared library,
`py_ballisticcalc_ctypes/_native_lib/libbclibc_ffi.so` (`.dylib` on macOS, `bclibc_ffi.dll` on Windows), with the bclibc core compiled
into it and a C ABI (`BCLIBCFFI_*`, 45 functions); it does not depend on the interpreter and is loaded at run time through ctypes. (The
Cython wheels link the core statically into each module.) On Pyodide the library is a WebAssembly side module and the platform tag names
the Pyodide ABI (`pyemscripten_*`): one wheel for each of Python 3.13, 3.14 and 3.15.

Tested in CI, every engine on every one: Linux x86_64, i686, aarch64, armv7l (glibc and musl), ppc64le, s390x and riscv64 (QEMU), macOS
arm64, universal2 and x86_64, Windows x64, x86 and ARM64, Android x86_64 (the arm64_v8a wheel is built, not run: there is no emulator),
Pyodide, PyPy 3.11, GraalPy 3.13 (Linux, Windows, macOS arm64; there is no macOS Intel build) and GraalPy 3.12 (Linux only: its ssl
module does not work on macOS and its tests hang on Windows).

## Development

```bash
uv sync --extra ctypes                       # builds the library with setup.py (the bclibc submodule must be initialised)
pytest --engine="cython+dopri"               # the main test suite on the ctypes engine, from the repository root
pytest py_ballisticcalc.ctypes/tests         # the tests of the package
```

* `PY_BALLISTICCALC_NATIVE_LIB_DIR=<dir>` uses a prebuilt `bclibc_ffi` library and skips the compile step.
* The bindings (`py_ballisticcalc_ctypes/_ctypesgen/_native_gen.py`) are generated from `bclibc_ffi.h` by ctypesgen (a development
  dependency, `ctypesgen==1.1.1`) with `regenerate_bindings.py`; a test fails when they are out of date.
* `_bclibc.py stage` copies the bclibc sources into the package for an sdist or a container build.
