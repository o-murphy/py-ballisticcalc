# cython: freethreading_compatible=True
"""
Cythonized Cash-Karp adaptive RK45 Integration Engine

EXPERIMENTAL -- see bclibc/cash_karp.hpp's own doc comment before relying on
this for anything accuracy-sensitive. The adaptive integrator itself is
validated (matches BCLIBC_integrateRK4 to numerical noise on a plain shot),
but tiny_bclibc/bclibc's shared event/row interpolation
(BCLIBC_interpolate3pt) derives its Hermite slopes via finite differences
across 3 raw points, which degrades once those points are sparse and
irregularly spaced -- exactly what this integrator produces on purpose
during smooth flight. Real, non-float-noise accuracy regressions have been
observed at exactly that boundary (see the project issue tracker).

Because storing each step in a BCLIBC_BaseTrajSeq is practically costless,
we always run with "dense_output=True" (matches rk4_engine/rk45_engine).
"""
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine, BCLIBC_IntegrateCallable

__all__ = [
    'CythonizedCashKarpIntegrationEngine',
]


cdef class CythonizedCashKarpIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized Cash-Karp (embedded adaptive RK45) integration engine for ballistic calculations."""

    def __cinit__(self, object config):
        # Same base step as RK4 -- this is only the *starting* step Cash-Karp
        # grows/shrinks from via its own adaptive error control, not a
        # separate tuning knob.
        self._DEFAULT_TIME_STEP = 0.0025
        self._this.integrate_func = BCLIBC_IntegrateCallable(BCLIBC_integrateCashKarp)

    def get_step_stats(self):
        """Returns (accepted, rejected) step counts from the most recent
        integration call -- the fairest comparison against a fixed-step
        method's own `integration_step_count` (which only counts
        accepted/emitted steps for both methods)."""
        cdef int accepted = 0
        cdef int rejected = 0
        BCLIBC_cashKarpGetStats(accepted, rejected)
        return accepted, rejected
