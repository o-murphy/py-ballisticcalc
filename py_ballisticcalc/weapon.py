from dataclasses import dataclass
from .unit import *


@dataclass
class Weapon:
    sight_height: Distance
    zero_distance: Distance = Distance(100, Distance.Yard)
    twist: Distance = Distance(0, Distance.Inch)
    click_value: Angular = Angular(0.25, Angular.MOA)
