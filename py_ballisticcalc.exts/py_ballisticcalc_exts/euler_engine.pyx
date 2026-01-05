# cython: freethreading_compatible=True
"""
Cythonized Euler Integration Engine

Because storing each step in a BCLIBC_BaseTrajSeq is practically costless,
we always run with "dense_output=True".
"""
from cython cimport final
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine, BCLIBC_IntegrateCallable

__all__ = [
    'CythonizedEulerIntegrationEngine',
]


@final
cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized Euler integration engine for ballistic calculations."""

    def __cinit__(self, object config):
        self._DEFAULT_TIME_STEP = 0.5  # Match Python's EulerIntegrationEngine.DEFAULT_TIME_STEP
        self._this.integrate_func = BCLIBC_IntegrateCallable(BCLIBC_integrateEULER)
