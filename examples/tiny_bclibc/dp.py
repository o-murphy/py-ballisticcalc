"""Double-precision tiny_bclibc integration engine (ctypes/FFI). See package `__init__.py`."""

import ctypes

from ._common import TinyBclibcIntegrationEngineBase

__all__ = ("TinyBclibcDoubleIntegrationEngine",)


class TinyBclibcDoubleIntegrationEngine(TinyBclibcIntegrationEngineBase):
    """RK4 integration engine whose per-step physics run inside double-precision tiny_bclibc.

    Built from a tiny_bclibc compiled *without* `TINY_BCLIBC_SINGLE_PRECISION` (`real_t =
    double`). Run this alongside `sp.TinyBclibcSingleIntegrationEngine` against the same test
    suite to tell apart genuine single-precision accumulation error from logic bugs shared by
    both (this ctypes binding, the raw-streaming addition to tiny_bclibc, or the RK4 core
    itself): a failure only the single-precision engine hits is (most likely) precision; a
    failure both hit is a bug.

    Requires the `PYBALLISTICCALC_TINY_BCLIBC_DP_LIB` environment variable to point at the
    compiled `libtiny_bclibc.so` (`.dylib`/`.dll`) — see `CMakeLists.txt` in this directory.

    Examples:
        >>> from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
        >>> config = BaseEngineConfigDict(cMinimumVelocity=0.0)
        >>> engine = TinyBclibcDoubleIntegrationEngine(config)
    """

    REAL_T = ctypes.c_double
    LIB_ENV_VAR = "PYBALLISTICCALC_TINY_BCLIBC_DP_LIB"
    PRECISION_LABEL = "double precision"
