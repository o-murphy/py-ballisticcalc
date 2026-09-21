"""tiny_bclibc integration engines (single- and double-precision), driven over ctypes/FFI.

This is example code, not part of the installed py_ballisticcalc package: it depends on
natively-compiled `tiny_bclibc` shared libraries that py_ballisticcalc does not ship or build
itself. Use `CMakeLists.txt` in this directory to build them (from the bclibc git submodule
already vendored at `py_ballisticcalc.exts/py_ballisticcalc_exts/external/bclibc` — see below),
and `run_example.py` for a runnable demo.

`tiny_bclibc` (see https://github.com/ballistics-lab/bclibc/tree/main/tiny_bclibc) is a pure
C99 reimplementation of the ballistic engine. The two engine classes below each load a compiled
build via ctypes and drive its filtered trajectory-streaming function
(`tiny_bclibc_integrate_stream`) from
[`BaseIntegrationEngine._integrate`][py_ballisticcalc.engines.base_engine.BaseIntegrationEngine];
`_common.py` holds the shared ctypes bindings, engine base class, and the row-coalescing/
finalize post-processing described under Architecture below.

Two engine classes are provided, built from the same code driving two separately-compiled
tiny_bclibc libraries (one with `TINY_BCLIBC_SINGLE_PRECISION`, `real_t = float`; one without,
`real_t = double`):

- `TinyBclibcSingleIntegrationEngine`
- `TinyBclibcDoubleIntegrationEngine`

Running both against the same pytest suite separates precision effects from logic bugs: a
failure that reproduces under *both* engines is a bug in this ctypes binding or the tiny_bclibc
core itself — not single-precision accumulation error. A failure that appears only under the
single-precision engine is (most likely) genuinely a float32-vs-float64 precision effect (see
`TinyBclibcSingleIntegrationEngine`'s docstring for the verified limits; the exact count varies
as the shared test suite evolves). The double-precision engine passes its applicable full suite
with one known exception (`test_hitresult.py::test_flags` -- see
`TinyBclibcDoubleIntegrationEngine`'s docstring), a cross-implementation FSAL rounding
difference against bclibc's C++ Tsitouras engine, not a logic bug.

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
    `_common.py`'s module docstring for what each closes and why. `zero_point` calls
    `tiny_bclibc_find_zero_point` directly and returns the native solver's terminal point, so
    `Calculator.aim()` does not repeat the Python zero-search loop. `zero_angle` uses the same
    native solver, with the established Python solver as a fallback for its unsupported extreme
    cases; `find_apex`/`find_max_range` remain `BaseIntegrationEngine` implementations and call
    `_integrate` (and therefore `tiny_bclibc_integrate_stream`) repeatedly, exactly as
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
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc:TinyBclibcSingleIntegrationEngine
    PYTHONPATH=examples uv run pytest --engine=tiny_bclibc:TinyBclibcDoubleIntegrationEngine
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

See Also:
    py_ballisticcalc.engines.rk4: Pure-Python RK4 engine these mirror architecturally.
    py_ballisticcalc.engines.base_engine.BaseIntegrationEngine: Base class.
"""

import ctypes

from ._common import TinyBclibcIntegrationEngineBase

__all__ = ("TinyBclibcSingleIntegrationEngine", "TinyBclibcDoubleIntegrationEngine")


class TinyBclibcSingleIntegrationEngine(TinyBclibcIntegrationEngineBase):
    """Tsitouras 5(4) adaptive integration engine whose per-step physics run inside single-precision tiny_bclibc.

    Built from a tiny_bclibc compiled with `TINY_BCLIBC_SINGLE_PRECISION` (`real_t = float`).
    See `TinyBclibcDoubleIntegrationEngine` for the double-precision counterpart used to
    separate precision effects from logic bugs.

    Requires the `PYBALLISTICCALC_TINY_BCLIBC_LIB` environment variable to point at the
    compiled `libtiny_bclibc.so` (`.dylib`/`.dll`) — see `CMakeLists.txt` in this directory.

    Defaults `cZeroFindingAccuracy` to `1e-3` ft (unless the caller sets it explicitly),
    matching tiny_bclibc's own `TINY_BCLIBC_SINGLE_PRECISION` zero-finding tolerance. The
    library-wide default (`5e-6` ft) is tighter than float32 can represent at typical zero
    distances (float32's ~7 significant digits give an absolute precision floor of roughly
    position_ft * 1.2e-7 -- about 8e-4 ft at 2000m), so with the default,
    `BaseIntegrationEngine`'s primary damped-Newton zero search can never converge and always
    falls back to the ~10-50x more expensive guaranteed method (`_find_zero_angle`, which
    itself requires a `_find_max_range` golden-section search first).

    Known precision limitation: `tiny_bclibc_integrate_stream`'s
    `TINY_BCLIBC_TrajectoryRequest.range_limit_ft` /
    `.range_step_ft` fields are `real_t`, so a requested target more precise than `real_t` can
    represent is already rounded at that C call boundary, before any physics or interpolation
    runs -- e.g. requesting an exact ~741 m range step is off by ~3e-5 m purely from that one
    rounding (confirmed empirically; see bclibc's tiny_bclibc CHANGELOG). This is inherent to
    driving tiny_bclibc's filtering/range-step API end-to-end in single precision, not a logic
    bug, and is why `test_issues.py::TestIssue144`'s 8 parametrizations (written for
    double-precision engines, `abs=1e-6` on a ~740 m distance) fail only here.
    `test_full_coriolis_by_latitude`, `test_hitresult.py::test_tiny_step`, and
    `test_mbc.py::test_mbc1`/`test_mbc2` compare values right at float32's precision floor
    (self-consistency checks between two independently-run single-precision trajectories, not
    against a fixed reference); `test_vertical_shot` accumulates float32's rounding of 90°=π/2
    over many adaptive steps into a ~0.01 ft position error. These predate the Tsitouras switch
    below (they fail identically under the previous Cash-Karp build) and are independent of
    which adaptive core `tiny_bclibc` runs.

    Additional single-precision-only failures since the Cash-Karp-\>Tsitouras switch (same
    root cause as the double-precision note below, just crossing tighter single-precision
    self-consistency tolerances that Cash-Karp's build happened to stay inside):
    `test_computer.py::test_cant_zero_elevation`/`test_cant_zero_sight_height`, and
    `test_mbc.py::test_mbc3`.

    Examples:
        >>> from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
        >>> config = BaseEngineConfigDict(cMinimumVelocity=0.0)
        >>> engine = TinyBclibcSingleIntegrationEngine(config)
    """

    REAL_T = ctypes.c_float
    LIB_ENV_VAR = "PYBALLISTICCALC_TINY_BCLIBC_LIB"
    PRECISION_LABEL = "single precision"
    DEFAULT_ZERO_FINDING_ACCURACY = 1e-3


class TinyBclibcDoubleIntegrationEngine(TinyBclibcIntegrationEngineBase):
    """Tsitouras 5(4) adaptive integration engine whose per-step physics run inside double-precision tiny_bclibc.

    Built from a tiny_bclibc compiled *without* `TINY_BCLIBC_SINGLE_PRECISION` (`real_t =
    double`). Run this alongside `TinyBclibcSingleIntegrationEngine` against the same test
    suite to tell apart genuine single-precision accumulation error from logic bugs shared by
    both (this ctypes binding, the raw-streaming addition to tiny_bclibc, or the Tsitouras
    core itself): a failure only the single-precision engine hits is (most likely) precision; a
    failure both hit is a bug.

    Requires the `PYBALLISTICCALC_TINY_BCLIBC_DP_LIB` environment variable to point at the
    compiled `libtiny_bclibc.so` (`.dylib`/`.dll`) — see `CMakeLists.txt` in this directory.

    Known issue: `test_hitresult.py::test_flags` fails here (but not under any Cython engine)
    because `tiny_bclibc`'s hand-written C Tsitouras port and bclibc's C++
    `BCLIBC_integrateTsitouras` are not bit-identical -- both individually correct, but the
    FSAL shortcut sums per-stage contributions in a different order than the C++ core's
    generic weighted-sum, and adaptive step-acceptance decisions are sensitive to that. For
    this specific shot (wind + calculated powder sensitivity) the MACH crossing lands about
    0.67 yd off out of 963 yd (0.07%), just outside that test's ±0.5 yd tolerance. Not a
    missed event and not a coefficient error -- see bclibc's CHANGELOG ("Known issues") for
    the full explanation.

    Examples:
        >>> from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
        >>> config = BaseEngineConfigDict(cMinimumVelocity=0.0)
        >>> engine = TinyBclibcDoubleIntegrationEngine(config)
    """

    REAL_T = ctypes.c_double
    LIB_ENV_VAR = "PYBALLISTICCALC_TINY_BCLIBC_DP_LIB"
    PRECISION_LABEL = "double precision"
