# cython: freethreading_compatible=True
"""
Cythonized RK4 Integration Engine

Because storing each step in a BCLIBC_BaseTrajSeq is practically costless,
we always run with "dense_output=True".
"""
# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine


__all__ = [
    'CythonizedRK4IntegrationEngine',
]


@final
cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized RK4 (Runge-Kutta 4th order) integration engine for ballistic calculations."""
    DEFAULT_TIME_STEP = 0.0025

    def __cinit__(self, object _config):
        self._engine.integrate_func_ptr = BCLIBC_integrateRK4

    cdef double get_calc_step(CythonizedRK4IntegrationEngine self):
        """Calculate the step size for integration."""
        return self.DEFAULT_TIME_STEP * CythonizedBaseIntegrationEngine.get_calc_step(self)
