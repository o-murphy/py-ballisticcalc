from typing_extensions import TypedDict, Optional
from py_ballisticcalc.trajectory_calc import (
    Config,
)
from py_ballisticcalc import trajectory_calc

__all__ = (
    "Config",
    "InterfaceConfigDict",
    "create_interface_config",
)


class InterfaceConfigDict(TypedDict, total=False):
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
        max_calc_step_size_feet=trajectory_calc._globalMaxCalcStepSizeFeet,
        chart_resolution=trajectory_calc._globalChartResolution,
        cZeroFindingAccuracy=trajectory_calc.cZeroFindingAccuracy,
        cMinimumVelocity=trajectory_calc.cMinimumVelocity,
        cMaximumDrop=trajectory_calc.cMaximumDrop,
        cMaxIterations=trajectory_calc.cMaxIterations,
        cGravityConstant=trajectory_calc.cGravityConstant,
        cMinimumAltitude=trajectory_calc.cMinimumAltitude,
    )
    if interface_config is not None and isinstance(interface_config, dict):
        config.update(interface_config)
    return Config(**config)
