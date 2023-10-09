"""Implements a point of trajectory class in applicable data types"""
from enum import Flag
from typing import NamedTuple

from .settings import Settings as Set
from .unit import Angular, Distance, Weight, Velocity, Energy, AbstractUnit, Unit

__all__ = ('TrajectoryData', 'TrajFlag')


class TrajFlag(Flag):
    """Flags for marking trajectory row if Zero or Mach crossing
    Also uses to set a filters for a trajectory calculation loop
    """
    NONE = 0
    ZERO_UP = 1
    ZERO_DOWN = 2
    MACH = 4
    RANGE = 8
    ZERO = ZERO_UP | ZERO_DOWN
    ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH


class TrajectoryData(NamedTuple):
    """
    Represents point of trajectory in applicable data types

    Attributes:
        time (float): bullet flight time
        distance (Distance): traveled distance
        velocity (Velocity): velocity in current trajectory point
        mach (float): velocity in current trajectory point in "Mach" number
        drop (Distance):
        drop_adj (Angular):
        windage (Distance):
        windage_adj (Angular):
        angle (Angular)
        mach float
        energy (Energy):
        ogw (Weight): optimal game weight
        rtype (int): row type
    """

    time: float
    distance: Distance
    velocity: Velocity
    mach: float  # velocity in Mach
    drop: Distance
    drop_adj: Angular  # drop_adjustment
    windage: Distance
    windage_adj: Angular  # windage_adjustment
    angle: Angular  # Trajectory angle
    energy: Energy
    ogw: Weight
    flag: TrajFlag

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
            _fmt(self.angle, Set.Units.angular),
            _fmt(self.energy, Set.Units.energy),
            _fmt(self.ogw, Set.Units.ogw),

            self.flag
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
            self.angle >> Set.Units.angular,
            self.energy >> Set.Units.energy,
            self.ogw >> Set.Units.ogw,

            self.flag
        )
