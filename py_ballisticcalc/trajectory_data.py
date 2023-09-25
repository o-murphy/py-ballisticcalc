from typing import NamedTuple

from .settings import DefaultUnits
from .unit import *

__all__ = ('TrajectoryData',)


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

    def formatted(self):

        def _fmt(v: AbstractUnit, u: Unit):
            return f"{v >> u:.{u.accuracy}f} {u.symbol}"

        return [
            f'{self.time:.2f} s',
            _fmt(self.distance, DefaultUnits.distance),
            _fmt(self.velocity, DefaultUnits.velocity),
            f'{self.mach:.2f} mach',
            _fmt(self.drop, DefaultUnits.drop),
            _fmt(self.drop_adj, DefaultUnits.adjustment),
            _fmt(self.windage, DefaultUnits.drop),
            _fmt(self.windage_adj, DefaultUnits.adjustment),
            _fmt(self.energy, DefaultUnits.energy)
        ]

    def in_def_units(self):
        return (
            self.time,
            self.distance >> DefaultUnits.distance,
            self.velocity >> DefaultUnits.velocity,
            self.mach,
            self.drop >> DefaultUnits.drop,
            self.drop_adj >> DefaultUnits.adjustment,
            self.windage >> DefaultUnits.drop,
            self.windage_adj >> DefaultUnits.adjustment,
            self.energy >> DefaultUnits.energy
        )
