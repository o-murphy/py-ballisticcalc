# Bindings over the C ABI of bclibc: prototypes and what they showed

> **Update (bclibc 2.2.0):** the Cython prototype is now the package [`py_ballisticcalc.cabi`](../../py_ballisticcalc.cabi)
> (`cabi+<method>` engines). bclibc 2.2 closed the gaps listed below: the buffer and the interpolation of base trajectory
> points (`BCLIBCFFI_base_traj_*`) and the error kinds (`BCLIBCFFI_ERR_DOMAIN`...) are in its C ABI, so `c/bclibc_ffi_ext.{h,c}`
> and the message matching of `_raise_get` are gone, and `bcffi.pxd` is `_bcffi.pxd`, generated from the real header with
> `BCLIBC_FFI_PARSE_ONLY`. The text below is the state of the prototype on bclibc 2.1.0; `cffi/` and `swig/` are unchanged.

An experiment, not part of any package. It asks one question: **if the engines were bound to `bclibc_ffi.h` (the C ABI,
`BCLIBCFFI_*`) instead of to the C++ API, how would the binding layer compare, and in which language?** The ABI is what
`py_ballisticcalc.ctypes` already uses. Three prototypes port its engine glue (`_native.py`): Cython (`cython/`), cffi
(`cffi/`) and SWIG (`swig/`). Everything was built and measured on Linux x86-64, CPython 3.13 (the Cython module is abi3,
`Py_LIMITED_API=0x030B0000`), bclibc 2.1.0.

## Cython over the C ABI (`cython/`, `c/`) — the one worth coming back to

The engines and the two public buffers of the C++ layer, `CythonizedBaseTrajSeq` and `CythonizedBaseTrajData` (the same names):
one file, `cython/bcy.pyx`; `cython/bcffi.pxd`, which **autopxd2 generates** from `c/bclibc_ffi_ext.h` (that header includes
`bclibc_ffi.h`: all `BCLIBCFFI_*` functions and types; no hand-written `.pxd`); and **plain C**, `c/bclibc_ffi_ext.{h,c}`, for what
the C ABI lacks and the C++ API has (below). The six engines (`Native<Method>IntegrationEngine`) have `nogil` around every C call.
It is built as **one static abi3 module** with the core and the C ABI wrapper compiled in (`cython/build.sh`): no shared
library, no `auditwheel`/`delocate`/`delvewheel`, nothing the C++ API of bclibc has to export.

```
PYTHON=<python with Cython>=3.1> cython/build.sh        # -> cython/build/bcy.abi3.so (555 KB, libstdc++ static)
PYTHONPATH=cython/build python cython/check.py          # the engines: bit-exact against py_ballisticcalc_exts
PYTHONPATH=cython/build python cython/check_seq.py      # the two buffer classes against the ones of py_ballisticcalc_exts: 12215 calls, 0 differences
PYTHONPATH=cython/build pytest tests --engine=bcy:NativeDormandPrinceIntegrationEngine          # the core suite, from the repository root
# the unmodified tests of py_ballisticcalc.exts, with bcy under the names they import:
PYTHONPATH=cython/build:experiments/cabi/tests pytest -p cabi_shim py_ballisticcalc.exts/tests/test_cbase_traj_seq.py ... --engine=bcy:NativeRK4IntegrationEngine
PYTHONPATH=cython/build python bench/layer.py           # the binding layer, with almost no C work (from the repository root)
```

Hand-written code, counted the same way for both (no blank lines, comments or docstrings; `_test_engine.pyx` and `_test_helpers.pyx`
of exts, which poke at C++ internals, are not counted there, and the timing probe `_probe` here):

| | Cython over C++ (`py_ballisticcalc.exts`) | Cython over the C ABI (this) |
|---|---|---|
| `.pyx` | 861 lines (4 files) | **599** (1 file) |
| C | | **123** (`bclibc_ffi_ext.{h,c}`; meant to move into bclibc) |
| hand-written `.pxd` | 820 (12 files) | **0** (257 generated) |
| **hand-written, all** | **1681** | **722**: 2.3 times less (2.8 times less once the C is in bclibc: 599) |
| binary | ~690 KB (4 modules) | 555 KB (1 module, libstdc++ static) |

The first version of this prototype did the engines only: 438 lines of `.pyx`, 3.8 times less than 1681. Bringing the scope up to the engines plus the two buffer classes took 161 more lines of Cython and the 123 of C.

Checked (Linux x86-64, CPython 3.13, bclibc 2.1.0):

* **the engines**: bit-exact (6 engines, `zero_point`, dense sequence), `cython/check.py`;
* **the two buffer classes**: 12215 calls on empty, one-, two-, three-point, long and degenerate sequences, every index, key
  and `start_from_time`: equal values and the same exception type, `cython/check_seq.py`;
* **the tests of exts** that do not depend on C++ internals, unmodified: `test_cbase_traj_seq`, `test_get_at_functions`,
  `test_trajectory_data_exts`, `test_cython_edges` (on RK4 and Dormand-Prince), and the opt-in `test_cython_leaks` and
  `test_cython_stress_memory`;
* **the core suite**: 387 passed, 32 skipped on each of the six engines.

Speed (`scripts/benchmark.py -w 300 -r 3000`, two interleaved rounds, minimum): on par with Cython over C++ within a few
percent. The binding layer alone (`bench/layer.py`, dopri, microseconds per call, minimum of 7 rounds; unchanged by the buffer
classes):

| | C++ | C ABI |
|---|---|---|
| `integrate_raw_at`, little C work | 14.4 | 11.6 |
| `zero_angle(100 m)` | 16.1 | 12.3 |
| `fire(10 m)`, full path with `HitResult` | 101.8 | 102.9 |

### What the C ABI lacks, and what was done about it

* **The buffer and the interpolation of `BaseTrajData`.** The C++ API has `BCLIBC_BaseTrajSeq` (a growing buffer),
  `BCLIBC_BaseTrajData::interpolate` and `BCLIBC_BaseTrajSeq::interpolate_at`; the C ABI has only `dense_get_at`,
  `dense_get_at_slant_height` and the array `integrate` returns. `c/bclibc_ffi_ext.c` adds them as the same kind of C functions
  (`BCLIBCFFI_base_traj_buf_*`, `BCLIBCFFI_base_traj_interpolate`, `BCLIBCFFI_base_traj_interpolate_at`), so a binding does not
  have to write them; they are meant to move into bclibc. `bcy.pyx` has only the Python side.
* **The kind of an error.** `setEngineError` in `bclibc_ffi.cpp` makes `BCLIBCFFI_ERR_GENERIC` of every error that is not a
  `Solver*` one, so an out-of-range and a domain error of `get_at` look alike, while the C++ layer raises `IndexError` for the first
  and `ValueError` for the second. `_raise_get` in `bcy.pyx` tells them apart by the message ("outside the trajectory's range"),
  which is fragile; a kind in `BCLIBCFFI_Error` would make it a switch on the code.

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

* **`test_memory_leak.py`, `test_python_parity.py` and `test_import_cython_modules.py` of exts** do not apply: they use
  `CythonEngineTestHarness` and the helpers that read a C++ `ShotProps` by its address (`_test_engine.pyx`, `_test_helpers.pyx`), and
  import the modules of `py_ballisticcalc_exts` by name. There is no such thing behind the C ABI.
* Built and run on Linux only. Windows (the C ABI has `dllexport`, the extension would link statically), macOS, Android, iOS
  and Pyodide are untried for this module; Pyodide builds of the C++ layer and of `py_ballisticcalc.ctypes` were tried and work.
* `bcffi.pxd` needs two edits after autopxd2 4.2.0: `cdef extern from` names `"bclibc_ffi_ext.h"` (the absolute path it prints is
  replaced) and the block gets `nogil` (without it Cython refuses the calls in `with nogil:`). Functions of an `extern` block are
  `noexcept` for Cython 3 already (checked in the generated C: no error test after the calls).
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
