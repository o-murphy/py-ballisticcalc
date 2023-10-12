"""Implements a point of trajectory class in applicable data types"""
import logging
from dataclasses import dataclass
from enum import Flag
from typing import NamedTuple

from .settings import Settings as Set
from .unit import Angular, Distance, Weight, Velocity, Energy, AbstractUnit, Unit

try:
    import pandas as pd
except ImportError as error:
    logging.warning("Install pandas to convert trajectory as dataframe")
    pd = None

try:
    import matplotlib
    from matplotlib import pyplot as plt
except ImportError as error:
    logging.warning("Install matplotlib to get results as a plot")
    matplotlib = None

__all__ = ('TrajectoryData', 'ShotTrajectory', 'TrajFlag',
           'trajectory_plot', 'trajectory_dataframe')


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
            TrajFlag(self.flag)
        )


@dataclass
class ShotTrajectory:
    """Results of the shot"""
    _trajectory: list[TrajectoryData]

    def __iter__(self):
        for row in self._trajectory:
            yield row

    def __getitem__(self, item):
        return self._trajectory[item]

    def zero_given_elevation(self) -> list[TrajectoryData]:
        """Find the zero distance for a given barrel elevation"""
        data = [row for row in self._trajectory if row.flag & TrajFlag.ZERO.value]
        if len(data) < 1:
            raise ArithmeticError("Can't found zero crossing points")
        return data


def trajectory_dataframe(shot_result: 'ShotTrajectory') -> 'DataFrame':
    """:return: the trajectory table as a DataFrame"""
    if pd is None:
        raise ImportError("Install pandas to convert trajectory as dataframe")

    col_names = TrajectoryData._fields
    trajectory = [p.in_def_units() for p in shot_result]
    return pd.DataFrame(trajectory, columns=col_names)


def trajectory_plot(calc: 'Calculator', shot: 'Shot',
                    current_atmo: 'Atmo' = None,
                    current_winds: list['Wind'] = None) -> 'plot':
    """:return: the graph of the trajectory"""

    if matplotlib is None:
        raise ImportError("Install matplotlib to get results as a plot")

    matplotlib.use('TkAgg')
    shot_result = calc.fire(shot, current_atmo, current_winds)
    df = trajectory_dataframe(shot_result)
    ax = df.plot(x='distance', y=['drop'], ylabel=Set.Units.drop.symbol)

    for p in shot_result:

        if TrajFlag(p.flag) & TrajFlag.ZERO:
            ax.plot([p.distance >> Set.Units.distance, p.distance >> Set.Units.distance],
                    [df['drop'].min(), p.drop >> Set.Units.drop], linestyle=':')
        if TrajFlag(p.flag) & TrajFlag.MACH:
            ax.plot([p.distance >> Set.Units.distance, p.distance >> Set.Units.distance],
                    [df['drop'].min(), p.drop >> Set.Units.drop], linestyle='--', label='mach')
            ax.text(p.distance >> Set.Units.distance, df['drop'].min(), " Mach")

    # # scope line
    x_values = [0, df.distance.max()]  # Adjust these as needed
    y_values = [0, 0]  # Adjust these as needed
    ax.plot(x_values, y_values, linestyle='--', label='scope line')
    ax.text(df.distance.max() - 100, -100, "Scope")

    df.plot(x='distance', xlabel=Set.Units.distance.symbol,
            y=['velocity'], ylabel=Set.Units.velocity.symbol,
            secondary_y=True,
            ylim=[0, df['velocity'].max()], ax=ax)

    return plt
