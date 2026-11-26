"""Temporary xfail for engines built against the old bclibc pin (no C26: time rows before range rows).

Remove this module and its usages at repin.
"""

import pytest

REPIN_REASON = "needs bclibc with C26 (time rows before range rows); remove at repin"
_ADAPTIVE = ("CashKarp", "DormandPrince", "Tsitouras")


def needs_repin(engine) -> bool:
    """Cythonized adaptive engines (rkck, dopri, tsitouras) and tiny_bclibc, which embed bclibc."""
    module = getattr(engine, "__module__", "") or ""
    if module.startswith("tiny_bclibc"):
        return True
    return module.startswith("py_ballisticcalc_exts") and any(k in engine.__name__ for k in _ADAPTIVE)


def xfail_until_repin(request, engine, reason: str = REPIN_REASON) -> None:
    """Non-strict xfail (XPASS is fine for new-bclibc builds) for the engines that need the repin only."""
    if needs_repin(engine):
        request.applymarker(pytest.mark.xfail(strict=False, reason=reason))


C18_REASON = "needs bclibc C18 check (repin)"


def is_cythonized(engine) -> bool:
    """Every engine that embeds bclibc (the cythonized ones and tiny_bclibc)."""
    module = getattr(engine, "__module__", "") or ""
    return module.startswith(("py_ballisticcalc_exts", "tiny_bclibc"))


def xfail_until_c18_repin(request, engine, reason: str = C18_REASON) -> None:
    """Non-strict xfail (XPASS is fine for new-bclibc builds) for the engines that lack the C18 check of a discontinuous root.

    The C26 helper above is left alone: it matches only the engines that lack the time-rows fix.
    """
    if is_cythonized(engine):
        request.applymarker(pytest.mark.xfail(strict=False, reason=reason))


CANT_REASON = "needs bclibc exact-cant solver frame (C37) ; remove at repin"


def xfail_until_cant_repin(request, engine, reason: str = CANT_REASON) -> None:
    """Non-strict xfail (XPASS is fine for new-bclibc builds) for the engines whose solver still uses the old cant frame.

    The Python solvers (and SciPy) search in the exact canted frame of `Shot` (C37); a bclibc built before that change
    solves with the elevation scaled by `cos(cant)` and so misses with a cant.  Only the cant tests that need the solver
    use this; the others (`Shot` getters and setter) are pure Python.
    """
    if is_cythonized(engine):
        request.applymarker(pytest.mark.xfail(strict=False, reason=reason))
