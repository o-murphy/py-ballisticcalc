from dataclasses import dataclass

from .unit import *


@dataclass
class WindInfo:
    """
    Represents wind info valid to desired distance

    Attributes:
        until_distance (Distance): default 9999 - represents inf
        velocity (Velocity): default 0
        direction (Angular): default 0
    """

    velocity: Velocity = Velocity(0, Velocity.FPS)
    direction: Angular = Angular(0, Angular.Degree)
    until_distance: Distance = Distance(9999, Distance.Kilometer)

