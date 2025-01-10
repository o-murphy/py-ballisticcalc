from py_ballisticcalc import Weapon, Ammo, Atmo
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

# @dataclass
class Shot:
    look_angle: Angular
    relative_angle: Angular
    cant_angle: Angular
    weapon: Weapon
    ammo: Ammo
    atmo: Atmo
    def __init__(self, weapon: Weapon, ammo: Ammo, look_angle: Optional[Union[float, Angular]] = None, relative_angle: Optional[Union[float, Angular]] = None, cant_angle: Optional[Union[float, Angular]] = None, atmo: Optional[Atmo] = None, winds: Optional[list[Wind]] = None) -> None: ...
    @property
    def winds(self) -> tuple[Wind, ...]: ...
    @winds.setter
    def winds(self, winds: Optional[list[Wind]]): ...
    @property
    def barrel_elevation(self) -> Angular: ...
    @property
    def barrel_azimuth(self) -> Angular: ...
