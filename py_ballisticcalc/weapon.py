from dataclasses import dataclass
from typing import NamedTuple

from .atmosphere import Atmosphere
from .bmath.unit import *
from .projectile import Ammunition


# from enum import IntEnum

# class TwistDir(IntEnum):
#     NONE = 0
#     RIGHT = 1
#     LEFT = 2

class ZeroInfo(NamedTuple):
    distance: Distance = Distance(100, DistanceYard)
    ammunition: Ammunition = None
    atmosphere: Atmosphere = None


@dataclass
class Weapon:
    sight_height: Distance
    zero_info: Distance
    twist: Distance = Distance(0, DistanceInch)
    click_value: Angular = Angular(0.25, AngularMOA)
