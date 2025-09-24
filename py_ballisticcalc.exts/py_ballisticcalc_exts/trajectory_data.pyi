from py_ballisticcalc.unit import Angular, Distance, Energy, Velocity, Weight
from typing_extensions import NamedTuple, Union, Tuple

__all__ = ['TrajectoryData']

class TrajectoryData(NamedTuple):
    __slots__: Tuple[str, ...]
    _field: Tuple[str, ...]

    time: float
    distance: Distance
    velocity: Velocity
    mach: float
    height: Distance
    slant_height: Distance
    drop_angle: Angular
    windage: Distance
    windage_angle: Angular
    slant_distance: Distance
    angle: Angular
    density_ratio: float
    drag: float
    energy: Energy
    ogw: Weight
    flag: Union[int]
    def formatted(self) -> tuple[str, ...]: ...
    def in_def_units(self) -> tuple[float, ...]: ...
