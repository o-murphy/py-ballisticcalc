"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.cashkarp_engine`
to improve IDE completion for the Cythonized Cash-Karp integration API.
"""

from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict

__all__ = ["CashKarpEngineConfig", "CythonizedCashKarpIntegrationEngine"]

class CashKarpEngineConfig(BaseEngineConfigDict, total=False):
    """Configuration accepted by :class:`CythonizedCashKarpIntegrationEngine`."""

    relative_tolerance: float

class CythonizedCashKarpIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized Cash-Karp (embedded adaptive RK45) integration engine for ballistic calculations.

    The ``relative_tolerance`` config key controls the embedded local-error
    estimate and defaults to ``1e-6``.
    """

    DEFAULT_TIME_STEP: float
    relative_tolerance: float

    def __init__(self, config: CashKarpEngineConfig | BaseEngineConfigDict | None = None) -> None:
        """Initialize with standard options and optional ``relative_tolerance``."""

    def get_step_stats(self) -> tuple[int, int]:
        """Returns (accepted, rejected) step counts from the most recent integration call."""
