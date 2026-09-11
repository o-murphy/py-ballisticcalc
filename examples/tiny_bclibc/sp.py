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
    compiled `libtiny_bclibc.so` (`.dylib`/`.dll`) — see `build_tiny_bclibc.sh`.

    Examples:
        >>> from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
        >>> config = BaseEngineConfigDict(cMinimumVelocity=0.0)
        >>> engine = TinyBclibcSingleIntegrationEngine(config)
    """

    REAL_T = ctypes.c_float
    LIB_ENV_VAR = "PYBALLISTICCALC_TINY_BCLIBC_LIB"
    PRECISION_LABEL = "single precision"
