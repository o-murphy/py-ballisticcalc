from .unit import *

__all__ = ('TrajectoryData', )


class TrajectoryData(NamedTuple):
    """
    Represents point of trajectory in applicable data types

    Attributes:
        time (float): bullet flight time
        distance (Distance): traveled distance
        velocity (Velocity): velocity in current trajectory point
        mach (float): velocity in current trajectory point in "Mach" number
        drop (Distance):
        drop_adj (Angular | None):
        windage (Distance):
        windage_adj (Angular | None):
        energy (Energy):
        ogw (Weight): optimal game weight
    """

    time: float
    distance: Distance
    velocity: Velocity
    mach: float
    drop: Distance
    drop_adj: Angular | None  # drop_adjustment
    windage: Distance
    windage_adj: Angular | None  # windage_adjustment
    energy: Energy
    ogw: Weight
