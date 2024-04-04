"""Implements a point of trajectory class in applicable data types"""
import logging
import math
import typing
from dataclasses import dataclass, field
from enum import Flag
from typing import NamedTuple

from .unit import Angular, Distance, Weight, Velocity, Energy, AbstractUnit, Unit, PreferredUnits
from .conditions import Shot

try:
    import pandas as pd
except ImportError as error:
    logging.warning("Install pandas to convert trajectory to dataframe")
    pd = None

try:
    import matplotlib
    from matplotlib import patches
except ImportError as error:
    logging.warning("Install matplotlib to get results as a plot")
    matplotlib = None

__all__ = ('TrajectoryData', 'HitResult', 'TrajFlag')

PLOT_FONT_HEIGHT = 72
PLOT_FONT_SIZE = 552 / PLOT_FONT_HEIGHT


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
    Data for one point in ballistic trajectory

    Attributes:
        time (float): bullet flight time
        distance (Distance): x-axis coordinate
        velocity (Velocity): velocity
        mach (float): velocity in Mach prefer_units
        height (Distance): y-axis coordinate
        target_drop (Distance): drop relative to sight-line
        drop_adj (Angular): sight adjustment to zero target_drop at this distance
        windage (Distance):
        windage_adj (Angular):
        look_distance (Distance): sight-line distance = .distance/cosine(look_angle)
        # look_height (Distance): y-coordinate of sight-line = .distance*tan(look_angle)
        angle (Angular): Angle of velocity vector relative to x-axis
        density_factor (float): Ratio of air density here to standard density
        drag (float): Current drag coefficient
        energy (Energy):
        ogw (Weight): optimal game weight
        flag (int): row type
    """

    time: float
    distance: Distance
    velocity: Velocity
    mach: float
    height: Distance
    target_drop: Distance
    drop_adj: Angular
    windage: Distance
    windage_adj: Angular
    look_distance: Distance
    angle: Angular
    density_factor: float
    drag: float
    energy: Energy
    ogw: Weight
    flag: typing.Union[TrajFlag, int]

    def formatted(self) -> tuple:
        """
        :return: matrix of formatted strings for each value of trajectory in default prefer_units
        """

        def _fmt(v: AbstractUnit, u: Unit):
            """simple formatter"""
            return f"{v >> u:.{u.accuracy}f} {u.symbol}"

        return (
            f'{self.time:.3f} s',
            _fmt(self.distance, PreferredUnits.distance),
            _fmt(self.velocity, PreferredUnits.velocity),
            f'{self.mach:.2f} mach',
            _fmt(self.height, PreferredUnits.drop),
            _fmt(self.target_drop, PreferredUnits.drop),
            _fmt(self.drop_adj, PreferredUnits.adjustment),
            _fmt(self.windage, PreferredUnits.drop),
            _fmt(self.windage_adj, PreferredUnits.adjustment),
            _fmt(self.look_distance, PreferredUnits.distance),
            _fmt(self.angle, PreferredUnits.angular),
            f'{self.density_factor:.3e}',
            f'{self.drag:.3f}',
            _fmt(self.energy, PreferredUnits.energy),
            _fmt(self.ogw, PreferredUnits.ogw),

            self.flag
        )

    def in_def_units(self) -> tuple:
        """
        :return: matrix of floats of the trajectory in default prefer_units
        """
        return (
            self.time,
            self.distance >> PreferredUnits.distance,
            self.velocity >> PreferredUnits.velocity,
            self.mach,
            self.height >> PreferredUnits.drop,
            self.target_drop >> PreferredUnits.drop,
            self.drop_adj >> PreferredUnits.adjustment,
            self.windage >> PreferredUnits.drop,
            self.windage_adj >> PreferredUnits.adjustment,
            self.look_distance >> PreferredUnits.distance,
            self.angle >> PreferredUnits.angular,
            self.density_factor,
            self.drag,
            self.energy >> PreferredUnits.energy,
            self.ogw >> PreferredUnits.ogw,
            TrajFlag(self.flag)
        )


class DangerSpace(NamedTuple):
    """Stores the danger space data for distance specified"""
    at_range: TrajectoryData
    target_height: Distance
    begin: TrajectoryData
    end: TrajectoryData
    look_angle: Angular

    def __str__(self) -> str:
        return f'Danger space at {self.at_range.distance << PreferredUnits.distance} ' \
            + f'for {self.target_height << PreferredUnits.drop} tall target ' \
            + (f'at {self.look_angle << Angular.Degree} look-angle ' if self.look_angle != 0 else '') \
            + f'ranges from {self.begin.distance << PreferredUnits.distance} ' \
            + f'to {self.end.distance << PreferredUnits.distance}'

    def overlay(self, ax: 'Axes', label: str = None):
        """Highlights danger-space region on plot"""
        if matplotlib is None:
            raise ImportError("Install matplotlib to get results as a plot")

        cosine = math.cos(self.look_angle >> Angular.Radian)
        begin_dist = (self.begin.distance >> PreferredUnits.distance) * cosine
        begin_drop = (self.begin.height >> PreferredUnits.drop) * cosine
        end_dist = (self.end.distance >> PreferredUnits.distance) * cosine
        end_drop = (self.end.height >> PreferredUnits.drop) * cosine
        range_dist = (self.at_range.distance >> PreferredUnits.distance) * cosine
        range_drop = (self.at_range.height >> PreferredUnits.drop) * cosine
        h = self.target_height >> PreferredUnits.drop

        # Target position and height:
        ax.plot((range_dist, range_dist), (range_drop + h / 2, range_drop - h / 2),
                color='r', linestyle=':')
        # Shaded danger-space region:
        vertices = (
            (begin_dist, begin_drop), (end_dist, begin_drop),
            (end_dist, end_drop), (begin_dist, end_drop)
        )
        polygon = patches.Polygon(vertices, closed=True,
                                  edgecolor='none', facecolor='r', alpha=0.3)
        ax.add_patch(polygon)
        if label is None:  # Add default label
            label = f"Danger space\nat {self.at_range.distance << PreferredUnits.distance}"
        if label != '':
            ax.text(begin_dist + (end_dist - begin_dist) / 2, end_drop, label,
                    linespacing=1.2, fontsize=PLOT_FONT_SIZE, ha='center', va='top')


@dataclass(frozen=True)
class HitResult:
    """Results of the shot"""
    shot: Shot
    trajectory: list[TrajectoryData] = field(repr=False)
    extra: bool = False

    def __iter__(self):
        yield from self.trajectory

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
            raise ArithmeticError("Can't find zero crossing points")
        return data

    def index_at_distance(self, d: Distance) -> int:
        """
        :param d: Distance for which we want Trajectory Data
        :return: Index of first trajectory row with .distance >= d; otherwise -1
        """
        # Get index of first trajectory point with distance >= at_range
        return next((i for i in range(len(self.trajectory))
                     if self.trajectory[i].distance >= d), -1)

    def get_at_distance(self, d: Distance) -> TrajectoryData:
        """
        :param d: Distance for which we want Trajectory Data
        :return: First trajectory row with .distance >= d
        """

        if i := self.index_at_distance(d) < 0:
            raise ArithmeticError(
                f"Calculated trajectory doesn't reach requested distance {d}"
            )
        return self.trajectory[i]

    def danger_space(self,
                     at_range: [float, Distance],
                     target_height: [float, Distance],
                     look_angle: [float, Angular] = None
                     ) -> DangerSpace:
        """
        Assume that the trajectory hits the center of a target at any distance.
        Now we want to know how much ranging error we can tolerate if the critical region 
        of the target has height *h*.  I.e., we want to know how far forward and backward
        along the line of sight we can move a target such that the trajectory is still 
        within *h*/2 of the original drop.

        :param at_range: Danger space is calculated for a target centered at this sight distance
        :param target_height: Target height (*h*) determines danger space
        :param look_angle: Ranging errors occur along the look angle to the target
        """
        self.__check_extra__()

        at_range = PreferredUnits.distance(at_range)
        target_height = PreferredUnits.distance(target_height)
        target_height_half = target_height.raw_value / 2.0
        if look_angle is None:
            look_angle = self.shot.look_angle
        else:
            look_angle = PreferredUnits.angular(look_angle)

        # Get index of first trajectory point with distance >= at_range
        if (index := self.index_at_distance(at_range)) < 0:
            raise ArithmeticError(
                f"Calculated trajectory doesn't reach requested distance {at_range}"
            )

        def find_begin_danger(row_num: int) -> TrajectoryData:
            """
            Beginning of danger space is last .distance' < .distance where
                (.drop' - target_center) >= target_height/2
            :param row_num: Index of the trajectory point for which we are calculating danger space
            :return: Distance marking beginning of danger space
            """
            center_row = self.trajectory[row_num]
            for prime_row in reversed(self.trajectory[:row_num]):
                if (prime_row.target_drop.raw_value - center_row.target_drop.raw_value) >= target_height_half:
                    return prime_row
            return self.trajectory[0]

        def find_end_danger(row_num: int) -> TrajectoryData:
            """
            End of danger space is first .distance' > .distance where
                (target_center - .drop') >= target_height/2
            :param row_num: Index of the trajectory point for which we are calculating danger space
            :return: Distance marking end of danger space
            """
            center_row = self.trajectory[row_num]
            for prime_row in self.trajectory[row_num + 1:]:
                if (center_row.target_drop.raw_value - prime_row.target_drop.raw_value) >= target_height_half:
                    return prime_row
            return self.trajectory[-1]

        return DangerSpace(self.trajectory[index],
                           target_height,
                           find_begin_danger(index),
                           find_end_danger(index),
                           look_angle)

    def dataframe(self, formatted: bool = False) -> 'DataFrame':
        """
        :param formatted: False for values as floats; True for strings with prefer_units
        :return: the trajectory table as a DataFrame
        """
        if pd is None:
            raise ImportError("Install pandas to get trajectory as dataframe")
        col_names = list(TrajectoryData._fields)
        if formatted:
            trajectory = [p.formatted() for p in self]
        else:
            trajectory = [p.in_def_units() for p in self]
        return pd.DataFrame(trajectory, columns=col_names)

    def plot(self, look_angle: Angular = None) -> 'Axes':
        """:return: graph of the trajectory"""
        if look_angle is None:
            look_angle = self.shot.look_angle

        if matplotlib is None:
            raise ImportError("Install matplotlib to plot results")
        if not self.extra:
            logging.warning("HitResult.plot: To show extended data"
                            "Use Calculator.fire(..., extra_data=True)")
        font_size = PLOT_FONT_SIZE
        df = self.dataframe()
        ax = df.plot(x='distance', y=['height'], ylabel=PreferredUnits.drop.symbol)
        max_range = self.trajectory[-1].distance >> PreferredUnits.distance

        for p in self.trajectory:
            if TrajFlag(p.flag) & TrajFlag.ZERO:
                ax.plot([p.distance >> PreferredUnits.distance, p.distance >> PreferredUnits.distance],
                        [df['height'].min(), p.height >> PreferredUnits.drop], linestyle=':')
                ax.text((p.distance >> PreferredUnits.distance) + max_range / 100, df['height'].min(),
                        f"{(TrajFlag(p.flag) & TrajFlag.ZERO).name}",
                        fontsize=font_size, rotation=90)
            if TrajFlag(p.flag) & TrajFlag.MACH:
                ax.plot([p.distance >> PreferredUnits.distance, p.distance >> PreferredUnits.distance],
                        [df['height'].min(), p.height >> PreferredUnits.drop], linestyle=':')
                ax.text((p.distance >> PreferredUnits.distance) + max_range / 100, df['height'].min(),
                        "Mach 1", fontsize=font_size, rotation=90)

        max_range_in_drop_units = self.trajectory[-1].distance >> PreferredUnits.drop
        # Sight line
        x_sight = [0, df.distance.max()]
        y_sight = [0, max_range_in_drop_units * math.tan(look_angle >> Angular.Radian)]
        ax.plot(x_sight, y_sight, linestyle='--', color=[.3, 0, .3, .5])
        # Barrel pointing line
        x_bbl = [0, df.distance.max()]
        y_bbl = [-(self.shot.weapon.sight_height >> PreferredUnits.drop),
                 max_range_in_drop_units * math.tan(self.trajectory[0].angle >> Angular.Radian)
                 - (self.shot.weapon.sight_height >> PreferredUnits.drop)]
        ax.plot(x_bbl, y_bbl, linestyle=':', color=[0, 0, 0, .5])
        # Line labels
        sight_above_bbl = y_sight[1] > y_bbl[1]
        angle = math.degrees(math.atan((y_sight[1] - y_sight[0]) / (x_sight[1] - x_sight[0])))
        ax.text(x_sight[1], y_sight[1], "Sight line", linespacing=1.2,
                rotation=angle, rotation_mode='anchor', transform_rotates_text=True,
                fontsize=font_size, color=[.3, 0, .3, 1], ha='right',
                va='bottom' if sight_above_bbl else 'top')
        angle = math.degrees(math.atan((y_bbl[1] - y_bbl[0]) / (x_bbl[1] - x_bbl[0])))
        ax.text(x_bbl[1], y_bbl[1], "Barrel pointing", linespacing=1.2,
                rotation=angle, rotation_mode='anchor', transform_rotates_text=True,
                fontsize=font_size, color='k', ha='right',
                va='top' if sight_above_bbl else 'bottom')
        # Plot velocity (on secondary axis)
        df.plot(x='distance', xlabel=PreferredUnits.distance.symbol,
                y=['velocity'], ylabel=PreferredUnits.velocity.symbol,
                secondary_y=True, color=[0, .3, 0, .5],
                ylim=[0, df['velocity'].max()], ax=ax)
        # Let secondary shine through
        ax.set_zorder(1)
        ax.set_facecolor([0, 0, 0, 0])

        return ax
