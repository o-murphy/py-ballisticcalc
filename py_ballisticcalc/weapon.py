from dataclasses import dataclass
from .bmath.unit import *


@dataclass
class Weapon:
    sight_height: Distance
    zero_distance: Distance = Distance(100, DistanceYard)
    twist: Distance = Distance(0, DistanceInch)
    click_value: Angular = Angular(0.25, AngularMOA)
