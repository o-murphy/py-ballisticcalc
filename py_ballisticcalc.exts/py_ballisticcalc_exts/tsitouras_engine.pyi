from py_ballisticcalc_exts.base_engine import CythonizedBaseIntegrationEngine

from py_ballisticcalc.engines.base_engine import BaseEngineConfigDict

class CythonizedTsitourasIntegrationEngine(CythonizedBaseIntegrationEngine[BaseEngineConfigDict]):
    relative_tolerance: float
    absolute_tolerance: float
    def __init__(self, config: BaseEngineConfigDict | None = None) -> None: ...
    def get_step_stats(self) -> tuple[int, int]: ...
