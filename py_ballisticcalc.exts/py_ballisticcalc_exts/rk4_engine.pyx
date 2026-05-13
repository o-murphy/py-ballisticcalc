# cython: freethreading_compatible=True
"""
Cythonized RK4 Integration Engine

Because storing each step in a BCLIBC_BaseTrajSeq is practically costless,
we always run with "dense_output=True".
"""
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine, BCLIBC_IntegrateCallable

__all__ = [
    'CythonizedRK4IntegrationEngine',
]


# @final intentionally omitted: with Py_LIMITED_API (abi3), PyType_FromSpec() enforces
# Py_TPFLAGS_BASETYPE and blocks cross-module Cython subclassing. _test_engine subclasses
# this type at the C level, so @final would break the abi3 build.
cdef class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized RK4 (Runge-Kutta 4th order) integration engine for ballistic calculations."""

    def __cinit__(self, object config):
        self._DEFAULT_TIME_STEP = 0.0025
        self._this.integrate_func = BCLIBC_IntegrateCallable(BCLIBC_integrateRK4)
