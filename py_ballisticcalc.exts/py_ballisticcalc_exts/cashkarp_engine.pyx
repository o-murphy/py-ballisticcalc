# cython: freethreading_compatible=True
"""
Cythonized Cash-Karp adaptive RK45 Integration Engine

Accepted intervals are streamed directly to trajectory handlers. Scheduled
samples and exact physical events are reconstructed from endpoint-Hermite
interpolation, so adaptive step spacing does not define public output rows.
"""
import math

from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine

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
        self._absolute_tolerance = 1e-6
        # integrate_func takes its own copy of the integrator; target() then
        # hands back a pointer straight at *that* copy (the one actually
        # driving integration), which self._integrator keeps for the life
        # of this engine instance.
        self._this.integrate_func = BCLIBC_CashKarpIntegrator()
        self._integrator = self._this.integrate_func.target[BCLIBC_CashKarpIntegrator]()

    def __init__(self, object config):
        """Configure Cash-Karp with standard engine options and SciPy-style tolerances.

        ``relative_tolerance`` and scalar ``absolute_tolerance`` are both
        Cash-Karp-specific and default to ``1e-6``. They use the same
        component-wise error scale as :func:`scipy.integrate.solve_ivp`:
        ``atol + rtol * max(abs(y), abs(y_new))`` for each of the six position
        and velocity state values, followed by an RMS norm. Lower values always
        require more accepted/attempted steps, but do NOT reliably improve
        accuracy: measured against a 5x-finer fixed-step RK4 reference,
        1e-6 gave both the fewest total steps and the best event-root
        (ZERO/MACH/APEX) accuracy of 1e-6/1e-7/1e-8/1e-9 -- tightening
        further was a pure loss on that data. Don't tighten this default
        without re-measuring first; see `BCLIBC_CashKarpIntegrator::set_relative_tolerance`'s
        own doc comment in bclibc/cash_karp.hpp for the numbers, and
        tests/test_cashkarp.py::test_cashkarp_accuracy_across_tolerances for
        the harness (project issue #350).
        """
        base_config = config
        relative_tolerance = 1e-6
        absolute_tolerance = 1e-6
        if isinstance(config, dict):
            base_config = config.copy()
            relative_tolerance = base_config.pop("relative_tolerance", relative_tolerance)
            absolute_tolerance = base_config.pop("absolute_tolerance", absolute_tolerance)
        self.relative_tolerance = relative_tolerance
        self.absolute_tolerance = absolute_tolerance
        CythonizedBaseIntegrationEngine.__init__(self, base_config)

    @property
    def relative_tolerance(self):
        """SciPy-style relative local-error tolerance (default: ``1e-6``)."""
        return self._relative_tolerance

    @relative_tolerance.setter
    def relative_tolerance(self, double tolerance):
        if not math.isfinite(tolerance) or tolerance <= 0.0:
            raise ValueError("relative_tolerance must be finite and positive")
        self._relative_tolerance = tolerance

    @property
    def absolute_tolerance(self):
        """Scalar SciPy-style absolute local-error tolerance (default: ``1e-6``).

        It is applied independently to all six state components; it is not a
        separate position or velocity tolerance.
        """
        return self._absolute_tolerance

    @absolute_tolerance.setter
    def absolute_tolerance(self, double tolerance):
        if not math.isfinite(tolerance) or tolerance < 0.0:
            raise ValueError("absolute_tolerance must be finite and non-negative")
        self._absolute_tolerance = tolerance

    cdef BCLIBC_ShotProps* _init_trajectory(
        CythonizedCashKarpIntegrationEngine self,
        object shot_info,
    ):
        self._integrator.set_relative_tolerance(self._relative_tolerance)
        self._integrator.set_absolute_tolerance(self._absolute_tolerance)
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
        self._integrator.get_stats(accepted, rejected)
        self._last_accepted = accepted
        self._last_rejected = rejected

    def get_step_stats(self):
        """Returns (accepted, rejected) step counts from *this instance's*
        most recent `integrate()` call -- the fairest comparison against a
        fixed-step method's own `integration_step_count` (which only counts
        accepted/emitted steps for both methods).

        Snapshotted right after `integrate()` returns rather than read live
        from `self._integrator.get_stats()` here so a caller reading
        `get_step_stats()` mid-integration (e.g. from another thread) sees
        the last *completed* run's counts rather than an in-progress one.
        """
        return self._last_accepted, self._last_rejected
