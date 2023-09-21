from dataclasses import dataclass

from .bmath.unit import *


@dataclass
class WindInfo:
    """
    Represents wind info valid to desired distance

    Attributes:
        until_distance (Distance): default 9999 - represents inf
        velocity (Velocity): default 0
        direction (Angular): default 0
    """

    until_distance: Distance = Distance(9999, DistanceKilometer)
    velocity: Velocity = Velocity(0, VelocityFPS)
    direction: Angular = Angular(0, AngularDegree)
