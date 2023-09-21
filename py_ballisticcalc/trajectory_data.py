from dataclasses import dataclass
from math import fmod, floor
from typing import NamedTuple

from .bmath.unit import *


# @dataclass
# class Timespan:
#     __slots__ = ('time', )
#
#     time: float
#
#     @property
#     def total_seconds(self) -> float:
#         return self.time
#
#     @property
#     def seconds(self) -> float:
#         return fmod(floor(self.time), 60)
#
#     @property
#     def minutes(self) -> float:
#         return fmod(floor(self.time / 60), 60)


class TrajectoryData(NamedTuple):
    """
    Represents point of trajectory in applicable data types

    Attributes:
        time (float): bullet flight time
        distance (Distance): traveled distance
        velocity (Velocity): velocity in current trajectory point
        mach (float): velocity in current trajectory point in "Mach" number
        drop (Distance):
        drop_adjustment (Angular | None):
        windage (Distance):
        windage_adjustment (Angular | None):
        energy (Energy):
        ogw (Weight): optimal game weight
    """

    time: float
    distance: Distance
    velocity: Velocity
    mach: float
    drop: Distance
    drop_adjustment: Angular | None
    windage: Distance
    windage_adjustment: Angular | None
    energy: Energy
    ogw: Weight
