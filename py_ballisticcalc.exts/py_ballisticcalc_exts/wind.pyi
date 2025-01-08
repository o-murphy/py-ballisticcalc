from py_ballisticcalc.constants import *
# from dataclasses import dataclass
from py_ballisticcalc.unit import Angular, Distance, Velocity
from typing_extensions import Optional, Union

__all__ = ['Wind']


# @dataclass
class Wind:
    velocity: Velocity
    direction_from: Angular
    until_distance: Distance
    MAX_DISTANCE_FEET: float = ...
    def __init__(self, velocity: Optional[Union[float, Velocity]] = None, direction_from: Optional[Union[float, Angular]] = None, until_distance: Optional[Union[float, Distance]] = None, *, max_distance_feet: Optional[float] = 100000000.0) -> None: ...
