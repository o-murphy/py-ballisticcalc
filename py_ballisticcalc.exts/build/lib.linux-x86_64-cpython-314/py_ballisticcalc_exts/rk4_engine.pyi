"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.rk4_engine`
to improve IDE completion for the Cythonized RK4 integration API.
"""

from typing import Any

from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

__all__ = ["CythonizedRK4IntegrationEngine"]

class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized RK4 (Runge-Kutta 4th order) integration engine for ballistic calculations."""

    # Class constant specific to RK4 engine
    DEFAULT_TIME_STEP: float

    def __cinit__(self, _config: Any) -> None:
        """
        C/C++-level initializer for the RK4 engine.
        Sets up the RK4 integration function pointer.
        """
        ...
