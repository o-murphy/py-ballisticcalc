# cython: freethreading_compatible=True
"""
Cythonized Euler Integration Engine

Because storing each step in a BaseTrajSeqT is practically costless, we always run with "dense_output=True".
"""
# noinspection PyUnresolvedReferences
from cython cimport final
# noinspection PyUnresolvedReferences
from py_ballisticcalc_exts.base_engine cimport CythonizedBaseIntegrationEngine

__all__ = [
    'CythonizedEulerIntegrationEngine',
]


@final
cdef class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized Euler integration engine for ballistic calculations."""
    DEFAULT_STEP = 0.5  # Match Python's EulerIntegrationEngine.DEFAULT_STEP

    def __cinit__(self, object _config):
        self._engine.integrate_func_ptr = _integrate_euler

    cdef double get_calc_step(CythonizedEulerIntegrationEngine self):
        """Calculate the step size for integration."""
        return self.DEFAULT_STEP * CythonizedBaseIntegrationEngine.get_calc_step(self)
