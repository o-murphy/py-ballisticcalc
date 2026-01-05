# cython: freethreading_compatible=True
"""
Cythonized RK4 Integration Engine

Because storing each step in a BCLIBC_BaseTrajSeq is practically costless,
we always run with "dense_output=True".
"""
from cython cimport final
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine, BCLIBC_IntegrateCallable

__all__ = [
    'CythonizedRK4IntegrationEngine',
]


@final
cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized RK4 (Runge-Kutta 4th order) integration engine for ballistic calculations."""

    def __cinit__(self, object config):
        self._DEFAULT_TIME_STEP = 0.0025
        self._this.integrate_func = BCLIBC_IntegrateCallable(BCLIBC_integrateRK4)
