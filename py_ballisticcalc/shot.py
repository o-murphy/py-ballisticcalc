from dataclasses import dataclass

from .unit import *

__all__ = ('ShotParameters', )


@dataclass
class ShotParameters:

    sight_angle: Angular
    max_range: Distance
    step: Distance
    shot_angle: Angular = Angular(0, Angular.Radian)
    cant_angle: Angular = Angular(0, Angular.Radian)
