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
