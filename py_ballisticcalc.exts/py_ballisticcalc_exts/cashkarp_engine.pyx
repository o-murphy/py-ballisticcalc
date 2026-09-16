# cython: freethreading_compatible=True
"""
Cythonized Cash-Karp adaptive RK45 Integration Engine

Accepted intervals are streamed directly to trajectory handlers. Scheduled
samples and exact physical events are reconstructed from endpoint-Hermite
interpolation, so adaptive step spacing does not define public output rows.
"""
import math

from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps
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
        self._relative_tolerance = 1e-6
        self._this.integrate_func = BCLIBC_IntegrateCallable(BCLIBC_integrateCashKarp)

    def __init__(self, object config):
        """Configure Cash-Karp with standard engine options and ``relative_tolerance``.

        ``relative_tolerance`` is Cash-Karp-specific and defaults to ``1e-6``.
        It controls the embedded local-error estimate. Lower values always
        require more accepted/attempted steps, but do NOT reliably improve
        accuracy: measured against a 5x-finer fixed-step RK4 reference,
        1e-6 gave both the fewest total steps and the best event-root
        (ZERO/MACH/APEX) accuracy of 1e-6/1e-7/1e-8/1e-9 -- tightening
        further was a pure loss on that data. Don't tighten this default
        without re-measuring first; see `BCLIBC_cashKarpSetRelativeTolerance`'s
        own doc comment in bclibc/cash_karp.hpp for the numbers, and
        tests/test_cashkarp.py::test_cashkarp_accuracy_across_tolerances for
        the harness (project issue #350).
        """
        base_config = config
        tolerance = 1e-6
        if isinstance(config, dict):
            base_config = config.copy()
            tolerance = base_config.pop("relative_tolerance", tolerance)
        self.relative_tolerance = tolerance
        CythonizedBaseIntegrationEngine.__init__(self, base_config)

    @property
    def relative_tolerance(self):
        """Relative local-error tolerance used by Cash-Karp (default: ``1e-6``)."""
        return self._relative_tolerance

    @relative_tolerance.setter
    def relative_tolerance(self, double tolerance):
        if not math.isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("relative_tolerance must be finite and positive")
        self._relative_tolerance = tolerance

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedCashKarpIntegrationEngine self,
        object shot_info,
    ):
        BCLIBC_cashKarpSetRelativeTolerance(self._relative_tolerance)
        return CythonizedBaseIntegrationEngine._init_trajectory(self, shot_info)

    def integrate(self, *args, **kwargs):
        """Same as the base engine's `integrate()`, additionally snapshotting
        this call's own step stats (see `get_step_stats()`)."""
        result = CythonizedBaseIntegrationEngine.integrate(self, *args, **kwargs)
        self._snapshot_step_stats()
        return result

    cdef void _snapshot_step_stats(CythonizedCashKarpIntegrationEngine self):
        cdef int accepted = 0
        cdef int rejected = 0
        BCLIBC_cashKarpGetStats(accepted, rejected)
        self._last_accepted = accepted
        self._last_rejected = rejected

    def get_step_stats(self):
        """Returns (accepted, rejected) step counts from *this instance's*
        most recent `integrate()` call -- the fairest comparison against a
        fixed-step method's own `integration_step_count` (which only counts
        accepted/emitted steps for both methods).

        Snapshotted right after `integrate()` returns rather than read live
        from `BCLIBC_cashKarpGetStats()` here, because that C-level counter
        is a thread-local *shared* across every
        `CythonizedCashKarpIntegrationEngine` instance on the same thread --
        reading it lazily would silently return whichever instance
        integrated *last* on this thread, not necessarily this one's own
        result, if another instance has integrated since.
        """
        return self._last_accepted, self._last_rejected
