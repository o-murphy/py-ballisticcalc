# cython: freethreading_compatible=True
"""
Cythonized Velocity Verlet Integration Engine

Because storing each step in a BCLIBC_BaseTrajSeq is practically costless,
we always run with "dense_output=True".
"""
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine, BCLIBC_IntegrateCallable

__all__ = [
    'CythonizedVelocityVerletIntegrationEngine',
]


# @final intentionally omitted: with Py_LIMITED_API (abi3), PyType_FromSpec() enforces
# Py_TPFLAGS_BASETYPE and blocks cross-module Cython subclassing.
# This class may be subclassed in the future — see rk4_engine.pyx for full context.
cdef class CythonizedVelocityVerletIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized Velocity Verlet integration engine for ballistic calculations."""

    def __cinit__(self, object config):
        self._DEFAULT_TIME_STEP = 0.001  # Match Python's VelocityVerletIntegrationEngine.DEFAULT_TIME_STEP
        self._this.integrate_func = BCLIBC_IntegrateCallable(BCLIBC_integrateVELOCITY_VERLET)
