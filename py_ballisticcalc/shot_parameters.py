from dataclasses import dataclass

from .bmath.unit import *


@dataclass
class ShotParameters:

    sight_angle: Angular
    range: Distance
    step: Distance
    shot_angle: Angular = Angular(0, AngularRadian)
    cant_angle: Angular = Angular(0, AngularRadian)
