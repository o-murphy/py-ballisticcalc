"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.rk4_engine`
to improve IDE completion for the Cythonized RK4 integration API.
"""

from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict
from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

__all__ = ["CythonizedRK45IntegrationEngine"]

class CythonizedRK45IntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized RK45 (Runge-Kutta 5th order) integration engine for ballistic calculations."""

    # Class constant specific to RK4 engine
    DEFAULT_TIME_STEP: float

    def __cinit__(self, _config: BaseEngineConfigDict) -> None:
        """
        C/C++-level initializer for the RK4 engine.
        Sets up the RK45 integration function pointer.
        """
        ...
