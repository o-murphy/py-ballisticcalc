from py_ballisticcalc.unit import Angular, Distance, Energy, Velocity, Weight
from typing_extensions import NamedTuple, Union

__all__ = ['TrajectoryData']

class TrajectoryData(NamedTuple):
    time: float
    distance: Distance
    velocity: Velocity
    mach: float
    height: Distance
    target_drop: Distance
    drop_adj: Angular
    windage: Distance
    windage_adj: Angular
    look_distance: Distance
    angle: Angular
    density_factor: float
    drag: float
    energy: Energy
    ogw: Weight
    flag: Union[int]
    def formatted(self) -> tuple[str, ...]: ...
    def in_def_units(self) -> tuple[float, ...]: ...
