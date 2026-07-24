"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.velocity_verlet_engine`
to improve IDE completion for the Cythonized Velocity Verlet integration API.
"""

from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict

__all__ = ["CythonizedVelocityVerletIntegrationEngine"]

class CythonizedVelocityVerletIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized Velocity Verlet integration engine for ballistic calculations."""

    # Class constant specific to Velocity Verlet engine
    DEFAULT_STEP: float  # Match Python's VelocityVerletIntegrationEngine.DEFAULT_TIME_STEP

    def __cinit__(self, config: BaseEngineConfigDict | None) -> None:
        """
        C/C++-level initializer for the Velocity Verlet engine.
        Sets up the Velocity Verlet integration function pointer.
        """
