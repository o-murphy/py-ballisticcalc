"""Implements a point of trajectory class in applicable data types"""
import logging
import math
from dataclasses import dataclass, field
from enum import Flag
from typing import NamedTuple, Callable

from .settings import Settings as Set
from .unit import Angular, Distance, Weight, Velocity, Energy, AbstractUnit, Unit

try:
    import pandas as pd
except ImportError as error:
    logging.warning("Install pandas to convert trajectory to dataframe")
    pd = None

try:
    import matplotlib
except ImportError as error:
    logging.warning("Install matplotlib to get results as a plot")
    matplotlib = None

__all__ = ('TrajectoryData', 'HitResult', 'TrajFlag',
           # 'trajectory_plot', 'trajectory_dataframe'
           )


class TrajFlag(Flag):
    """Flags for marking trajectory row if Zero or Mach crossing
    Also uses to set a filters for a trajectory calculation loop
    """
    NONE = 0
    ZERO_UP = 1
    ZERO_DOWN = 2
    MACH = 4
    RANGE = 8
    DANGER = 16
    ZERO = ZERO_UP | ZERO_DOWN
    ALL = RANGE | ZERO_UP | ZERO_DOWN | MACH | DANGER


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


class DangerSpace(NamedTuple):
    """Stores the danger space data for distance specified"""
    at_range: TrajectoryData
    target_height: Distance
    begin: TrajectoryData
    end: TrajectoryData

    def overlay(self, df):
        if matplotlib is None:
            raise ImportError("Install matplotlib to get results as a plot")
        else:
            begin = self.begin.distance >> Set.Units.distance
            begin_drop = self.begin.drop >> Set.Units.drop
            end = self.end.distance >> Set.Units.distance
            end_drop = self.end.drop >> Set.Units.drop
            h = (self.target_height >> Set.Units.drop) / 2
            df.plot([begin, begin], [begin_drop+h, begin_drop-h])
            df.plot([end, end], [end_drop+h, end_drop-h])




@dataclass(frozen=True)
class HitResult:
    """Results of the shot"""
    trajectory: list[TrajectoryData] = field(repr=False)
    extra: bool = False

    def __iter__(self):
        for row in self.trajectory:
            yield row

    def __getitem__(self, item):
        return self.trajectory[item]

    def __check_extra__(self):
        if not self.extra:
            raise AttributeError(
                f"{object.__repr__(self)} has no extra data. "
                f"Use Calculator.fire(..., extra_data=True)"
            )

    def zeros(self) -> list[TrajectoryData]:
        """:return: zero crossing points"""
        self.__check_extra__()
        data = [row for row in self.trajectory if row.flag & TrajFlag.ZERO.value]
        if len(data) < 1:
            raise ArithmeticError("Can't found zero crossing points")
        return data

    def danger_space(self,
                     at_range: [float, Distance],
                     target_height: [float, Distance],
                     look_angle: [float, Angular] = Angular(0, Angular.Degree)
                     ) -> DangerSpace:
        """
        Assume that the trajectory hits the center of a target at any distance.
        Now we want to know
        how much ranging error we can tolerate if the critical region of the target has height *h*.
        I.e., we want to know how far forward and backward along the line of sight we can
        move a target
        such that the trajectory is still within *h*/2 of the original drop.

        :param at_range: Danger space is calculated for a target centered at this distance
        :param target_height: Target height (*h*) determines danger space
        :param look_angle: Ranging errors occur along the look angle to the target
        """
        self.__check_extra__()

        at_range = Set.Units.distance(at_range)
        target_height = Set.Units.distance(target_height)
        look_angle = Set.Units.angular(look_angle)

        # Get index of first trajectory point with distance >= at_range
        i = next((i for i in range(len(self.trajectory))
                  if self.trajectory[i].distance >= at_range), -1)
        if i < 0:
            raise ArithmeticError(
                f"Calculated trajectory doesn't reach requested distance {at_range}"
            )

        target_height_half = target_height.raw_value / 2.0
        tan_look_angle = math.tan(look_angle >> Angular.Radian)

        # Target_center height shifts along look_angle as:
        #   target_center' = target_center + (.distance' - .distance) * tan(look_angle)

        def find_begin_danger(row_num: int) -> TrajectoryData:
            """
            Beginning of danger space is last .distance' < .distance where 
                |target_center - .drop'| >= target_height/2
            :param row_num: Index of the trajectory point for which we are calculating danger space
            :return: Distance marking beginning of danger space
            """
            center_row = self.trajectory[row_num]
            for i in range(row_num - 1, 0, -1):
                prime_row = self.trajectory[i]
                target_center = center_row.drop.raw_value + tan_look_angle * (
                        prime_row.distance.raw_value - center_row.distance.raw_value
                )
                if abs(target_center - prime_row.drop.raw_value) >= target_height_half:
                    return self.trajectory[i]
            return Distance.Yard(0)

        def find_end_danger(row_num: int) -> [TrajectoryData, None]:
            """
            End of danger space is first .distance' > .distance where 
                |target_center - .drop'| >= target_height/2
            :param row_num: Index of the trajectory point for which we are calculating danger space
            :return: Distance marking end of danger space
            """
            center_row = self.trajectory[row_num]
            for i in range(row_num + 1, len(self.trajectory)):
                prime_row = self.trajectory[i]
                target_center = center_row.drop.raw_value + tan_look_angle * (
                        prime_row.distance.raw_value - center_row.distance.raw_value)
                if abs(target_center - prime_row.drop.raw_value) >= target_height_half:
                    return prime_row
            return None

        return DangerSpace(self.trajectory[i],
                           target_height,
                           find_begin_danger(i),
                           find_end_danger(i))

    @property
    def dataframe(self):
        """:return: the trajectory table as a DataFrame"""
        if pd is None:
            raise ImportError("Install pandas to convert trajectory as dataframe")
        self.__check_extra__()
        col_names = list(TrajectoryData._fields)
        trajectory = [p.in_def_units() for p in self]
        return pd.DataFrame(trajectory, columns=col_names)

    def plot(self):
        """:return: the graph of the trajectory"""

        if matplotlib is None:
            raise ImportError("Install matplotlib to get results as a plot")
        if not self.extra:
            logging.warning("HitResult.plot: To show extended data"
                            "Use Calculator.fire(..., extra_data=True)")

        df = self.dataframe
        ax = df.plot(x='distance', y=['drop'], ylabel=Set.Units.drop.symbol)

        for p in self:

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
        return ax
