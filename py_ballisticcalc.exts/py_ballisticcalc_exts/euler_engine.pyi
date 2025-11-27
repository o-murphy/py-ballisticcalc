"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.euler_engine`
to improve IDE completion for the Cythonized Euler integration API.
"""

from typing import Any

from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

__all__ = ["CythonizedEulerIntegrationEngine"]

class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine):
    """Cythonized Euler integration engine for ballistic calculations."""

    # Class constant specific to Euler engine
    DEFAULT_STEP: float  # Match Python's EulerIntegrationEngine.DEFAULT_STEP

    def __cinit__(self, _config: Any) -> None:
        """
        C/C++-level initializer for the Euler engine.
        Sets up the Euler integration function pointer.
        """
        ...
