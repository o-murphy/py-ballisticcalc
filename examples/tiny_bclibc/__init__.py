"""tiny_bclibc integration engines (single- and double-precision), driven over ctypes/FFI.

This is example code, not part of the installed py_ballisticcalc package: it depends on
natively-compiled `tiny_bclibc` shared libraries that py_ballisticcalc does not ship or build
itself. Use `build_tiny_bclibc.sh` in this directory to build them, and `run_example.py` for a
runnable demo.

`tiny_bclibc` (see https://github.com/ballistics-lab/bclibc/tree/main/tiny_bclibc) is a pure
C99 reimplementation of the ballistic engine. `sp.py` / `dp.py` each load a compiled build via
ctypes and drive its raw RK4 stepping function (`tiny_bclibc_integrate_raw`) from
[`BaseIntegrationEngine._integrate`][py_ballisticcalc.engines.base_engine.BaseIntegrationEngine];
`_common.py` holds the shared ctypes bindings and engine base class.

Two engine classes are provided, built from the same code driving two separately-compiled
tiny_bclibc libraries (one with `TINY_BCLIBC_SINGLE_PRECISION`, `real_t = float`; one without,
`real_t = double`):

- `sp.TinyBclibcSingleIntegrationEngine`
- `dp.TinyBclibcDoubleIntegrationEngine`

Running both against the same pytest suite separates precision effects from logic bugs: a
failure that reproduces under *both* engines is a bug in this ctypes binding, the raw-streaming
addition to tiny_bclibc, or the tiny_bclibc RK4 core itself — not single-precision accumulation
error. A failure that appears only under the single-precision engine is (most likely) genuinely
a float32-vs-float64 precision effect.

Architecture:
    Only the numerically-sensitive per-step RK4 integration (position/velocity update under
    drag, gravity, wind, and Coriolis) runs inside the compiled C code. Every other algorithm —
    trajectory-point filtering/interpolation, zero-angle search, apex, max-range — is inherited
    unmodified from `BaseIntegrationEngine`/`TrajectoryDataFilter` and runs in Python (double
    precision), exactly as it does for
    [`EulerIntegrationEngine`][py_ballisticcalc.engines.euler.EulerIntegrationEngine] and
    [`RK4IntegrationEngine`][py_ballisticcalc.engines.rk4.RK4IntegrationEngine]. This isolates
    the effect of tiny_bclibc's precision to the RK4 core itself, so either engine can be run
    against the full py_ballisticcalc pytest suite like any other engine — e.g.:
    ```bash
    ./build_tiny_bclibc.sh                  # single precision -> bclibc/tiny_bclibc/build
    ./build_tiny_bclibc.sh bclibc double     # double precision -> bclibc/tiny_bclibc/build_double
    export PYBALLISTICCALC_TINY_BCLIBC_LIB=$(pwd)/bclibc/tiny_bclibc/build/libtiny_bclibc.so
    export PYBALLISTICCALC_TINY_BCLIBC_DP_LIB=$(pwd)/bclibc/tiny_bclibc/build_double/libtiny_bclibc.so
    cd ../..  # repo root
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc.sp:TinyBclibcSingleIntegrationEngine
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc.dp:TinyBclibcDoubleIntegrationEngine
    ```

Requirements:
    Build tiny_bclibc as a shared library from the `bclibc` repository, once per precision (see
    `build_tiny_bclibc.sh`). Then point `PYBALLISTICCALC_TINY_BCLIBC_LIB` (single) /
    `PYBALLISTICCALC_TINY_BCLIBC_DP_LIB` (double) at the resulting `libtiny_bclibc.so`
    (`.dylib`/`.dll`). Each library is loaded lazily on first use of its engine class, so
    importing this package never requires either to be present.

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
