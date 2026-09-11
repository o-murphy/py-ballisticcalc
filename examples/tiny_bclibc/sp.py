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

    Examples:
        >>> from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
        >>> config = BaseEngineConfigDict(cMinimumVelocity=0.0)
        >>> engine = TinyBclibcSingleIntegrationEngine(config)
    """

    REAL_T = ctypes.c_float
    LIB_ENV_VAR = "PYBALLISTICCALC_TINY_BCLIBC_LIB"
    PRECISION_LABEL = "single precision"
    DEFAULT_ZERO_FINDING_ACCURACY = 1e-3
