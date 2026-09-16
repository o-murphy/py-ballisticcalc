"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.cashkarp_engine`
to improve IDE completion for the Cythonized Cash-Karp integration API.
"""

from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict

__all__ = ["CythonizedCashKarpIntegrationEngine"]

class CythonizedCashKarpIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    """Cythonized Cash-Karp (embedded adaptive RK45) integration engine for ballistic calculations.

    EXPERIMENTAL -- see the project issue tracker for known event-
    interpolation accuracy regressions under this method's sparse/irregular
    step spacing before relying on this for anything accuracy-sensitive.
    """

    DEFAULT_TIME_STEP: float

    def __cinit__(self, _config: BaseEngineConfigDict) -> None:
        """C/C++-level initializer: sets up the Cash-Karp integration function pointer."""

    def get_step_stats(self) -> tuple[int, int]:
        """Returns (accepted, rejected) step counts from the most recent integration call."""
