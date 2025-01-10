from typing_extensions import TypedDict, Optional
from py_ballisticcalc.trajectory_calc import (
    Config,
    cZeroFindingAccuracy, cMinimumVelocity, cMaximumDrop, cMaxIterations,
    cGravityConstant, cMinimumAltitude,
    _globalChartResolution,
    _globalMaxCalcStepSizeFeet,
    _globalUsePowderSensitivity,
)

__all__ = (
    "Config",
    "InterfaceConfigDict",
    "create_interface_config",
)


class InterfaceConfigDict(TypedDict, total=False):
    use_powder_sensitivity: bool
    max_calc_step_size_feet: float
    chart_resolution: float
    cZeroFindingAccuracy: float
    cMinimumVelocity: float
    cMaximumDrop: float
    cMaxIterations: int
    cGravityConstant: float
    cMinimumAltitude: float


def create_interface_config(interface_config: Optional[InterfaceConfigDict] = None) -> Config:
    config = InterfaceConfigDict(
        use_powder_sensitivity=_globalUsePowderSensitivity,
        max_calc_step_size_feet=_globalMaxCalcStepSizeFeet,
        chart_resolution=_globalChartResolution,
        cZeroFindingAccuracy=cZeroFindingAccuracy,
        cMinimumVelocity=cMinimumVelocity,
        cMaximumDrop=cMaximumDrop,
        cMaxIterations=cMaxIterations,
        cGravityConstant=cGravityConstant,
        cMinimumAltitude=cMinimumAltitude,
    )
    if interface_config is not None and isinstance(interface_config, dict):
        config.update(interface_config)
    return Config(**config)
