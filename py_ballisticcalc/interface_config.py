from typing_extensions import TypedDict, Optional

from py_ballisticcalc.unit import Distance
from py_ballisticcalc.trajectory_calc import (
    cZeroFindingAccuracy, cMinimumVelocity, cMaximumDrop, cMaxIterations,
    cGravityConstant,
    get_global_max_calc_step_size, get_global_use_powder_sensitivity, Config
)

__all__ = (
    "Config",
    "InterfaceConfigDict",
    "create_interface_config",
)


class InterfaceConfigDict(TypedDict, total=False):
    use_powder_sensitivity: bool
    max_calc_step_size_feet: float
    cZeroFindingAccuracy: float
    cMinimumVelocity: float
    cMaximumDrop: float
    cMaxIterations: float
    cGravityConstant: float

def create_interface_config(interface_config: Optional[InterfaceConfigDict] = None) -> Config:
    config = InterfaceConfigDict(
        use_powder_sensitivity=get_global_use_powder_sensitivity(),
        max_calc_step_size_feet=get_global_max_calc_step_size() >> Distance.Foot,
        cZeroFindingAccuracy=cZeroFindingAccuracy,
        cMinimumVelocity=cMinimumVelocity,
        cMaximumDrop=cMaximumDrop,
        cMaxIterations=cMaxIterations,
        cGravityConstant=cGravityConstant,
    )
    if interface_config is not None and isinstance(interface_config, dict):
        config.update(interface_config)
    return Config(**config)
