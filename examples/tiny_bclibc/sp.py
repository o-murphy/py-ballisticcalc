"""Single-precision tiny_bclibc integration engine (ctypes/FFI). See package `__init__.py`."""

import ctypes

from ._common import TinyBclibcIntegrationEngineBase

__all__ = ("TinyBclibcSingleIntegrationEngine",)


class TinyBclibcSingleIntegrationEngine(TinyBclibcIntegrationEngineBase):
    """RK4 integration engine whose per-step physics run inside single-precision tiny_bclibc.

    Built from a tiny_bclibc compiled with `TINY_BCLIBC_SINGLE_PRECISION` (`real_t = float`).
    See `dp.TinyBclibcDoubleIntegrationEngine` for the double-precision counterpart used to
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

    Known precision limitation (11 of 375 tests in the full pytest suite, all with tolerances
    tighter than float32's ~7 significant digits; `dp.TinyBclibcDoubleIntegrationEngine` passes
    all 375): `tiny_bclibc_integrate_stream`'s `TINY_BCLIBC_TrajectoryRequest.range_limit_ft` /
    `.range_step_ft` fields are `real_t`, so a requested target more precise than `real_t` can
    represent is already rounded at that C call boundary, before any physics or interpolation
    runs -- e.g. requesting an exact ~741 m range step is off by ~3e-5 m purely from that one
    rounding (confirmed empirically; see bclibc's tiny_bclibc CHANGELOG). This is inherent to
    driving tiny_bclibc's filtering/range-step API end-to-end in single precision, not a logic
    bug, and is why `test_issues.py::TestIssue144` (written for double-precision engines, `abs
    =1e-6` on a ~740 m distance) fails only here. The two other failures
    (`test_wind_lag_rule`, `test_full_coriolis_by_latitude`) compare values near float32's
    precision floor directly; `test_vertical_shot` accumulates float32's rounding of 90°=π/2
    over ~18000 RK4 steps into a ~0.01 ft position error.

    Examples:
        >>> from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
        >>> config = BaseEngineConfigDict(cMinimumVelocity=0.0)
        >>> engine = TinyBclibcSingleIntegrationEngine(config)
    """

    REAL_T = ctypes.c_float
    LIB_ENV_VAR = "PYBALLISTICCALC_TINY_BCLIBC_LIB"
    PRECISION_LABEL = "single precision"
    DEFAULT_ZERO_FINDING_ACCURACY = 1e-3
