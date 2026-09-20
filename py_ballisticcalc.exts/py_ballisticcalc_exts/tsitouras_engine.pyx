# cython: freethreading_compatible=True
"""Compiled adaptive Tsitouras 5(4) ("Tsit5") engine."""
import math
from py_ballisticcalc_exts.base_types cimport BCLIBC_ShotProps
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine, BCLIBC_IntegrateCallable

__all__ = ['CythonizedTsitourasIntegrationEngine']

cdef class CythonizedTsitourasIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Adaptive Tsitouras 5(4) engine with SciPy-style tolerances."""
    def __cinit__(self, object config):
        self._DEFAULT_TIME_STEP = 0.0025
        self._relative_tolerance = 1e-6
        self._absolute_tolerance = 1e-6
        self._this.integrate_func = BCLIBC_IntegrateCallable(BCLIBC_integrateTsitouras)

    def __init__(self, object config):
        base_config = config
        rtol, atol = 1e-6, 1e-6
        if isinstance(config, dict):
            base_config = config.copy()
            rtol = base_config.pop('relative_tolerance', rtol)
            atol = base_config.pop('absolute_tolerance', atol)
        self.relative_tolerance = rtol
        self.absolute_tolerance = atol
        CythonizedBaseIntegrationEngine.__init__(self, base_config)

    @property
    def relative_tolerance(self): return self._relative_tolerance

    @relative_tolerance.setter
    def relative_tolerance(self, double value):
        if not math.isfinite(value) or value <= 0:
            raise ValueError('relative_tolerance must be finite and positive')
        self._relative_tolerance = value

    @property
    def absolute_tolerance(self):
        return self._absolute_tolerance

    @absolute_tolerance.setter
    def absolute_tolerance(self, double value):
        if not math.isfinite(value) or value < 0:
            raise ValueError('absolute_tolerance must be finite and non-negative')
        self._absolute_tolerance = value

    cdef BCLIBC_ShotProps* _init_trajectory(self, object shot_info):
        BCLIBC_tsitourasSetRelativeTolerance(self._relative_tolerance)
        BCLIBC_tsitourasSetAbsoluteTolerance(self._absolute_tolerance)
        return CythonizedBaseIntegrationEngine._init_trajectory(self, shot_info)

    def integrate(self, *args, **kwargs):
        cdef int accepted = 0
        cdef int rejected = 0
        result = CythonizedBaseIntegrationEngine.integrate(self, *args, **kwargs)
        BCLIBC_tsitourasGetStats(accepted, rejected)
        self._last_accepted, self._last_rejected = accepted, rejected
        return result

    def get_step_stats(self): return self._last_accepted, self._last_rejected
