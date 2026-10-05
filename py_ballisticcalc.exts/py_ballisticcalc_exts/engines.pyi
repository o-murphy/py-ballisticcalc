"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.engines`
to improve IDE completion for the Cythonized integration engine API.
"""

from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict

__all__ = [
    "CashKarpEngineConfig",
    "CythonizedCashKarpIntegrationEngine",
    "CythonizedDormandPrinceIntegrationEngine",
    "CythonizedEulerIntegrationEngine",
    "CythonizedRK4IntegrationEngine",
    "CythonizedTsitourasIntegrationEngine",
    "CythonizedVelocityVerletIntegrationEngine",
    "DormandPrinceEngineConfig",
    "TsitourasEngineConfig",
]

class CythonizedEulerIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized Euler integration engine for ballistic calculations."""

    # Class constant specific to Euler engine
    DEFAULT_STEP: float  # Match Python's EulerIntegrationEngine.DEFAULT_STEP

    def __cinit__(self, config: BaseEngineConfigDict | None) -> None:
        """
        C/C++-level initializer for the Euler engine.
        Sets up the Euler integration function pointer.
        """

class CythonizedRK4IntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized RK4 (Runge-Kutta 4th order) integration engine for ballistic calculations."""

    # Class constant specific to RK4 engine
    DEFAULT_TIME_STEP: float

    def __cinit__(self, config: BaseEngineConfigDict | None) -> None:
        """
        C/C++-level initializer for the RK4 engine.
        Sets up the RK4 integration function pointer.
        """

class CythonizedVelocityVerletIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized Velocity Verlet integration engine for ballistic calculations."""

    # Class constant specific to Velocity Verlet engine
    DEFAULT_STEP: float  # Match Python's VelocityVerletIntegrationEngine.DEFAULT_TIME_STEP

    def __cinit__(self, config: BaseEngineConfigDict | None) -> None:
        """
        C/C++-level initializer for the Velocity Verlet engine.
        Sets up the Velocity Verlet integration function pointer.
        """

class CashKarpEngineConfig(BaseEngineConfigDict, total=False):
    """Configuration accepted by :class:`CythonizedCashKarpIntegrationEngine`."""

    relative_tolerance: float
    absolute_tolerance: float

class CythonizedCashKarpIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized Cash-Karp (embedded adaptive RK45) integration engine for ballistic calculations.

    The scalar ``relative_tolerance`` and ``absolute_tolerance`` config keys
    control the embedded local-error estimate with ``solve_ivp`` semantics.
    Both default to ``1e-6``.
    """

    DEFAULT_TIME_STEP: float
    relative_tolerance: float
    absolute_tolerance: float

    def __init__(self, config: CashKarpEngineConfig | BaseEngineConfigDict | None = None) -> None:
        """Initialize with standard options and optional SciPy-style tolerances."""

    def get_step_stats(self) -> tuple[int, int]:
        """Returns (accepted, rejected) step counts from the most recent integration call."""

class DormandPrinceEngineConfig(BaseEngineConfigDict, total=False):
    """Configuration accepted by :class:`CythonizedDormandPrinceIntegrationEngine`.

    Attributes:
        relative_tolerance: Relative local-error tolerance (rtol), finite and positive. Default ``1e-6``.
        absolute_tolerance: Scalar absolute local-error tolerance (atol), finite and non-negative.
            Applied to all six state components. Default ``1e-6``.
    """

    relative_tolerance: float
    absolute_tolerance: float

class CythonizedDormandPrinceIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized Dormand-Prince 5(4) integration engine with ``solve_ivp``-style tolerances."""

    DEFAULT_TIME_STEP: float
    relative_tolerance: float
    absolute_tolerance: float

    def __init__(self, config: DormandPrinceEngineConfig | BaseEngineConfigDict | None = None) -> None: ...
    def get_step_stats(self) -> tuple[int, int]:
        """Returns (accepted, rejected) step counts from the most recent integration call."""

class TsitourasEngineConfig(BaseEngineConfigDict, total=False):
    """Configuration accepted by :class:`CythonizedTsitourasIntegrationEngine`.

    Attributes:
        relative_tolerance: Relative local-error tolerance (rtol), finite and positive. Default ``1e-6``.
        absolute_tolerance: Scalar absolute local-error tolerance (atol), finite and non-negative.
            Applied to all six state components. Default ``1e-6``.
    """

    relative_tolerance: float
    absolute_tolerance: float

class CythonizedTsitourasIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized Tsitouras 5(4) integration engine with ``solve_ivp``-style tolerances."""

    DEFAULT_TIME_STEP: float
    relative_tolerance: float
    absolute_tolerance: float

    def __init__(self, config: TsitourasEngineConfig | BaseEngineConfigDict | None = None) -> None: ...
    def get_step_stats(self) -> tuple[int, int]:
        """Returns (accepted, rejected) step counts from the most recent integration call."""
