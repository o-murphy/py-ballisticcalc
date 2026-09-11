"""tiny_bclibc integration engines (single- and double-precision), driven over ctypes/FFI.

This is example code, not part of the installed py_ballisticcalc package: it depends on
natively-compiled `tiny_bclibc` shared libraries that py_ballisticcalc does not ship or build
itself. Use `CMakeLists.txt` in this directory to build them (from the bclibc git submodule
already vendored at `py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc` — see below),
and `run_example.py` for a runnable demo.

`tiny_bclibc` (see https://github.com/ballistics-lab/bclibc/tree/main/tiny_bclibc) is a pure
C99 reimplementation of the ballistic engine. `sp.py` / `dp.py` each load a compiled build via
ctypes and drive its filtered trajectory-streaming function (`tiny_bclibc_integrate_stream`)
from
[`BaseIntegrationEngine._integrate`][py_ballisticcalc.engines.base_engine.BaseIntegrationEngine];
`_common.py` holds the shared ctypes bindings, engine base class, and the row-coalescing/
finalize post-processing described under Architecture below.

Two engine classes are provided, built from the same code driving two separately-compiled
tiny_bclibc libraries (one with `TINY_BCLIBC_SINGLE_PRECISION`, `real_t = float`; one without,
`real_t = double`):

- `sp.TinyBclibcSingleIntegrationEngine`
- `dp.TinyBclibcDoubleIntegrationEngine`

Running both against the same pytest suite separates precision effects from logic bugs: a
failure that reproduces under *both* engines is a bug in this ctypes binding or the tiny_bclibc
core itself — not single-precision accumulation error. A failure that appears only under the
single-precision engine is (most likely) genuinely a float32-vs-float64 precision effect (see
`sp.TinyBclibcSingleIntegrationEngine`'s docstring for the specific, verified mechanisms behind
its 11 known failures out of the full 375-test suite; `dp.TinyBclibcDoubleIntegrationEngine`
passes all 375).

Architecture:
    Both the RK4 integration itself and its range-step/APEX/MACH/ZERO filtering and
    derived-field computation (density_ratio, drag, spin drift, Coriolis-adjusted range,
    slant_height, angles, energy, ogw) run inside the compiled C code via
    `tiny_bclibc_integrate_stream` — Python's callback only fires once per *output* row, not
    once per raw RK4 step, which is what makes this fast (roughly cythonized_rk4_engine-scale
    on a Trajectory/Zero microbenchmark, vs. tens of milliseconds when streaming every raw
    step). `_common.py` closes two gaps against tiny_bclibc's C-side filtering in Python
    (`_coalesce_rows`, `_maybe_finalize`) rather than in tiny_bclibc itself, to keep that
    library's C surface minimal — it targets bare-metal/MCU embedding, where code size is a
    real constraint and neither gap is needed by tiny_bclibc's own native consumers. See
    `_common.py`'s module docstring for what each closes and why. `zero_angle`/`find_apex`/
    `find_max_range` themselves are still `BaseIntegrationEngine`'s own Python implementations,
    unmodified — they just call `_integrate` (and therefore `tiny_bclibc_integrate_stream`)
    repeatedly, exactly as
    [`EulerIntegrationEngine`][py_ballisticcalc.engines.euler.EulerIntegrationEngine] and
    [`RK4IntegrationEngine`][py_ballisticcalc.engines.rk4.RK4IntegrationEngine] do. Either
    engine can be run against the full py_ballisticcalc pytest suite like any other engine —
    e.g. from the repo root:
    ```bash
    git submodule update --init py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc
    cmake -B examples/tiny_bclibc/build -S examples/tiny_bclibc
    cmake --build examples/tiny_bclibc/build
    export PYBALLISTICCALC_TINY_BCLIBC_LIB=$(pwd)/examples/tiny_bclibc/build/single/libtiny_bclibc.so
    export PYBALLISTICCALC_TINY_BCLIBC_DP_LIB=$(pwd)/examples/tiny_bclibc/build/double/libtiny_bclibc.so
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc.sp:TinyBclibcSingleIntegrationEngine
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc.dp:TinyBclibcDoubleIntegrationEngine
    ```

Requirements:
    Build tiny_bclibc as a shared library, once per precision, via `CMakeLists.txt` in this
    directory — it reuses the bclibc git submodule already vendored for the Cython engine at
    `py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc` rather than fetching a second,
    independently-versioned copy of bclibc. Then point `PYBALLISTICCALC_TINY_BCLIBC_LIB`
    (single) / `PYBALLISTICCALC_TINY_BCLIBC_DP_LIB` (double) at the resulting
    `libtiny_bclibc.so` (`.dylib`/`.dll`). Each library is loaded lazily on first use of its
    engine class, so importing this package never requires either to be present.

Modules:
    _common: Shared ctypes bindings + `TinyBclibcIntegrationEngineBase`.
    sp: `TinyBclibcSingleIntegrationEngine` (float).
    dp: `TinyBclibcDoubleIntegrationEngine` (double).

See Also:
    py_ballisticcalc.engines.rk4: Pure-Python RK4 engine these mirror architecturally.
    py_ballisticcalc.engines.base_engine.BaseIntegrationEngine: Base class.
"""

from .dp import TinyBclibcDoubleIntegrationEngine
from .sp import TinyBclibcSingleIntegrationEngine

__all__ = ("TinyBclibcSingleIntegrationEngine", "TinyBclibcDoubleIntegrationEngine")
