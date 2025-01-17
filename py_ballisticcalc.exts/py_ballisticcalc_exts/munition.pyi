from dataclasses import dataclass
from py_ballisticcalc.drag_model import DragModel
from py_ballisticcalc.unit import Angular, Distance, Temperature, Velocity
from py_ballisticcalc.munition._munition import Sight
from typing_extensions import Optional, Union

__all__ = ['Weapon', 'Ammo']

@dataclass
class Weapon:
    sight_height: Distance
    twist: Distance
    zero_elevation: Angular
    sight: Optional['Sight']
    def __init__(self, sight_height: Optional[Union[float, Distance]] = None, twist: Optional[Union[float, Distance]] = None, zero_elevation: Optional[Union[float, Angular]] = None, sight: Optional[Sight] = None) -> None: ...

@dataclass
class Ammo:
    dm: DragModel
    mv: Velocity
    powder_temp: Temperature
    temp_modifier: float
    use_powder_sensitivity: bool = ...
    def __init__(self, dm: DragModel, mv: Union[float, Velocity], powder_temp: Optional[Union[float, Temperature]] = None, temp_modifier: float = 0, use_powder_sensitivity: bool = False) -> None: ...
    def calc_powder_sens(self, other_velocity: Union[float, Velocity], other_temperature: Union[float, Temperature]) -> float: ...
    def get_velocity_for_temp(self, current_temp: Union[float, Temperature]) -> Velocity: ...
