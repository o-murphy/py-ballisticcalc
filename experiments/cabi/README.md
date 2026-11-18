# Bindings over the C ABI of bclibc: prototypes and what they showed

An experiment, not part of any package. It asks one question: **if the engines were bound to `bclibc_ffi.h` (the C ABI,
`BCLIBCFFI_*`) instead of to the C++ API, how would the binding layer compare, and in which language?** The ABI is what
`py_ballisticcalc.ctypes` already uses. Three prototypes port its engine glue (`_native.py`): Cython (`cython/`), cffi
(`cffi/`) and SWIG (`swig/`). Everything was built and measured on Linux x86-64, CPython 3.13 (the Cython module is abi3,
`Py_LIMITED_API=0x030B0000`), bclibc 2.1.0.

## Cython over the C ABI (`cython/`) — the one worth coming back to

One file, `bcy.pyx` (397 lines of code, comments and blank lines excluded), plus `bcffi.pxd`, which **autopxd2 generates**
from `bclibc_ffi.h` (all 45 functions and 24 types; no hand-written `.pxd`). The six engines of the Cython layer
(`Native<Method>IntegrationEngine`), with `nogil` around every C call. It is built as **one static abi3 module** with the core
and the C ABI wrapper compiled in (`build.sh`): no shared library, no `auditwheel`/`delocate`/`delvewheel`, nothing the C++
API of bclibc has to export.

```
PYTHON=<python with Cython>=3.1> ./build.sh              # -> build/bcy.abi3.so (470 KB; 346 KB with the C++ runtime dynamic)
PYTHONPATH=build python check.py                         # bit-exact parity with py_ballisticcalc_exts
PYTHONPATH=build pytest tests --engine=bcy:NativeDormandPrinceIntegrationEngine      # from the repository root
PYTHONPATH=build python experiments/cabi/bench/layer.py  # the binding layer, with almost no C work
```

| | Cython over C++ (`py_ballisticcalc.exts`) | Cython over the C ABI (this) |
|---|---|---|
| hand-written code, `.pyx` | 837 lines (4 files) | **397** (1 file) |
| hand-written `.pxd` | 820 lines | **0** (331 generated) |
| binary | ~690 KB (4 modules) | **346 KB** (1 module, dynamic libstdc++); 470 KB with it static |
| results | | bit-exact: 6 engines, `zero_point`, dense sequence; the core suite passes (387 passed on RK4 and dopri) |

Speed (`scripts/benchmark.py -w 300 -r 3000`, two interleaved rounds, minimum): on par with Cython over C++ within a few
percent. The binding layer alone (`bench/layer.py`, dopri, microseconds per call, minimum of 7 rounds):

| | C++ | C ABI |
|---|---|---|
| `integrate_raw_at`, little C work | 14.3 | 11.6 |
| `zero_angle(100 m)` | 16.2 | 13.1 |
| `fire(10 m)`, full path with `HitResult` | 105.5 | 104.4 |

### Where the speed comes from — read before drawing conclusions

It did **not** come from the C ABI. Two things were done in the prototype, and one of them was then done in the C++ layer too:

* Building the result. `TrajectoryData` is a `NamedTuple`; the Cython layer built it through the Python `__new__` with sixteen
  keyword arguments and ten calls of `TrajectoryData._new_feet` & co. per record (8.7 us for three records). `tuple.__new__`
  with the unit objects created inline and a dict for `TrajFlag` takes 3.4 us. **The same change is in the C++ layer and in
  ctypes** (commits `2b33750` and `be0531a` of `claude/friendly-cori-gp97db`); with it both Cython layers are equal on `fire`.
* A cache of the drag table (a Python list of 84 points) and of the config, per engine. The C++ layer converts them on every
  call. The cache is what makes `zero_angle` and `raw_at` faster, and it costs correctness: its key is `(length, first
  point, last point)`, so an edit of a middle point in place is not seen. **It was not wanted in the C++ layer.**
* A `cdef class` that owns the array the library allocated for the dense steps, instead of copying it into `bytes`. The C++
  layer already has this (`CythonizedBaseTrajSeq`).

`nogil` on every C call: three threads, each with its own engine, `zero_angle(1500 m)` with RK4: throughput x3.14 (x2.87
for the C++ layer); without `nogil` on those calls x0.99. (Do not add `nogil` to the O(1) lookups of the sequence: it costs
more than the work, +25..40% on 0.25 us.)

## What is not done

* Only the engines. `CythonizedBaseTrajSeq`, `CythonizedBaseTrajData`, the test helper modules and the rest of `py_ballisticcalc.exts`
  are not ported, and `py_ballisticcalc.exts/tests` were not run against it.
* Built and run on Linux only. Windows (the C ABI has `dllexport`, the extension would link statically), macOS, Android, iOS
  and Pyodide are untried for this module; Pyodide builds of the C++ layer and of `py_ballisticcalc.ctypes` were tried and work.
* `bcffi.pxd` needs two edits after autopxd2 4.2.0: the absolute path in `cdef extern from` becomes
  `"bclibc/ffi/bclibc_ffi.h"`, and the block gets `nogil` (without it Cython refuses the calls in `with nogil:`). Functions of an
  `extern` block are `noexcept` for Cython 3 already (checked in the generated C: no error test after the calls).
* The scratch state per engine is not thread safe for one engine instance used by several threads (as in the C++ layer: one
  engine instance per thread).
* `bcy.pyx` ends with `_probe`, a timing probe of the three stages of the path (`bench/probe.py`): fill 4.6, C call 3.4,
  result 3.4 us for three records. Remove it for a real module.

## cffi and SWIG (`cffi/`, `swig/`) — scripts only, kept so they are not lost

Mechanical ports of `_native.py` (`port.py`, `port_swig.py` rewrite the ctypes calls), not maintained, paths are those of
a scratch directory. Results, with the same engines and the same checks (bit-exact):

* **cffi, API mode, `py_limited_api=True`**: really a code generator (5777 lines of C from the 521-line preprocessed header;
  `cpp -P`, with the `__attribute__((visibility))` of `BCLIBC_API` removed); builds `_bcffi.abi3.so`. It needs `_cffi_backend`
  at run time, and is **no faster than ctypes** (adaptive `Zero` 1.11..1.13 of Cython, ctypes 1.06..1.09).
* **SWIG 4.5.1**: abi3 works in the default mode only (`-builtin` does not compile with `Py_LIMITED_API`); the proxy classes
  make it the slowest (adaptive `Trajectory` +13..16%, `Zero` +24..35% over Cython).

## Other results of the same session, on `claude/friendly-cori-gp97db`

ctypes needs no change for Pyodide beyond building the library as a side module (done, and tested in the CI workflow);
the C++ Cython extensions link to a shared `libbclibc.so` in Pyodide with `-Wl,-rpath,$ORIGIN` (tried locally, tests pass,
not adopted); on PyPy 8.0 a ctypes structure does not export the buffer interface (fixed, with a regression test in
`py_ballisticcalc.ctypes/tests`).
