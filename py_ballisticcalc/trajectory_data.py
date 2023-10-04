"""Implements a point of trajectory class in applicable data types"""

from typing import NamedTuple

from .settings import Settings as Set
from .unit import Angular, Distance, Weight, Velocity, Energy, AbstractUnit, Unit

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
    drop_adj: Angular  # drop_adjustment
    windage: Distance
    windage_adj: Angular  # windage_adjustment
    energy: Energy
    ogw: Weight

    def formatted(self) -> tuple:
        """
        :return: matrix of formatted strings for each value of trajectory in default units
        """
        def _fmt(v: AbstractUnit, u: Unit):
            """simple formatter"""
            return f"{v >> u:.{u.accuracy}f} {u.symbol}"

        return (
            f'{self.time:.2f} s',
            _fmt(self.distance, Set.Units.distance),
            _fmt(self.velocity, Set.Units.velocity),
            f'{self.mach:.2f} mach',
            _fmt(self.drop, Set.Units.drop),
            _fmt(self.drop_adj, Set.Units.adjustment),
            _fmt(self.windage, Set.Units.drop),
            _fmt(self.windage_adj, Set.Units.adjustment),
            _fmt(self.energy, Set.Units.energy)
        )

    def in_def_units(self) -> tuple:
        """
        :return: matrix of floats of the trajectory in default units
        """
        return (
            self.time,
            self.distance >> Set.Units.distance,
            self.velocity >> Set.Units.velocity,
            self.mach,
            self.drop >> Set.Units.drop,
            self.drop_adj >> Set.Units.adjustment,
            self.windage >> Set.Units.drop,
            self.windage_adj >> Set.Units.adjustment,
            self.energy >> Set.Units.energy
        )
