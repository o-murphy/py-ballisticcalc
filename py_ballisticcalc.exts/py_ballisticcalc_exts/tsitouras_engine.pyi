"""
Type stubs for the compiled extension module `py_ballisticcalc_exts.tsitouras_engine`
to improve IDE completion for the Cythonized Tsitouras 5(4) integration API.
"""

from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict

__all__ = ["CythonizedTsitourasIntegrationEngine", "TsitourasEngineConfig"]

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
