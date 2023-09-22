from dataclasses import dataclass

from .unit import *

__all__ = ('Shot',)


@dataclass
class Shot:

    sight_angle: Angular
    max_range: Distance
    step: Distance
    shot_angle: Angular = Angular(0, Angular.Radian)
    cant_angle: Angular = Angular(0, Angular.Radian)
