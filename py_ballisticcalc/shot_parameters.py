from dataclasses import dataclass

from .unit import *


@dataclass
class ShotParameters:

    sight_angle: Angular
    range: Distance
    step: Distance
    shot_angle: Angular = Angular(0, Angular.Radian)
    cant_angle: Angular = Angular(0, Angular.Radian)
